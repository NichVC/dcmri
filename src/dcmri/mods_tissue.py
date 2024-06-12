import numpy as np
import dcmri as dc


class SteadyState(dc.Model):
    # Abstract base class to avoid some duplication in this module

    dt = 0.5
    Hct = 0.45
    agent = 'gadoterate'
    field_strength = 3.0
    TR = 0.005
    FA = 15
    R10 = 1
    R10b = 1
    t0 = 1
    S0 = 1 

    def __init__(self, aif, **kwargs):
        super().__init__(**kwargs)
        n0 = max([round(self.t0/self.dt),1])
        r1 = dc.relaxivity(self.field_strength, 'blood', self.agent)
        cb = dc.conc_ss(aif, self.TR, self.FA, 1/self.R10b, r1, n0)
        self.r1 = r1                                #: Relaxivity Hz/M
        self.ca = cb/(1-self.Hct)                   #: Arterial plasma concentration (M)
        self.t = self.dt*np.arange(np.size(aif))    #: Time points of the AIF (sec)

    def train(self, xdata, ydata, **kwargs):
        Sref = dc.signal_ss(self.R10, 1, self.TR, self.FA)
        n0 = max([np.sum(xdata<self.t0), 1])
        self.S0 = np.mean(ydata[:n0]) / Sref
        return super().train(xdata, ydata, **kwargs)


class UptSS(SteadyState):
    """One-compartment uptake tissue, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Plasma flow into the compartment per unit tissue.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `OneCompSS`, `PatlakSS`, `ToftsSS`, `EToftsSS`, `TwoCompUptWXSS`, `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.UptSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 229.188 (8.902) a.u.
        Plasma flow (Fp): 0.001 (0.0) 1/sec
    """   

    Fp = 0.01
    free = ['Fp']
    bounds = (0, np.inf)     

    def conc(self)->np.ndarray:
        """Tissue concentration.

        Returns:
            np.ndarray: Concentration in M
        """
        return dc.conc_1cum(self.ca, self.Fp, dt=self.dt)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF.'
            raise ValueError(msg)
        C = self.conc()
        R1 = self.R10 + self.r1*C
        ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        pars = {
            'Fp': ['Plasma flow',self.Fp,'mL/sec/mL'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)
    
    
# Fast/no water exchange
    

class OneCompSS(SteadyState):
    """One-compartment tissue, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Plasma flow into the compartment per unit tissue.
        - **v** (Volume of distribution, mL/mL): Volume fraction of the compartment. 
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `PatlakSS`, `ToftsSS`, `EToftsSS`, `TwoCompUptWXSS`, `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.OneCompSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)       
        -----------------------------------------       
        Signal scaling factor (S0): 175.126 (6.654) a.u.
        Plasma flow (Fp): 0.004 (0.0) 1/sec
        Volume of distribution (v): 0.004 (0.015) mL/mL 
    """ 
 
    Fp = 0.01
    v = 0.05
    free = ['Fp','v']
    bounds = (0, [np.inf, 1])
    water_exchange = True

    def conc(self)->np.ndarray:
        """Tissue concentration.

        Returns:
            np.ndarray: Concentration in M
        """
        return dc.conc_1cm(self.ca, self.Fp, self.v, dt=self.dt)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc()
        if self.water_exchange:
            R1 = self.R10 + self.r1*C
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            R1e = self.R10 + self.r1*C/self.v
            R1c = self.R10 + np.zeros(C.size)
            v = [self.v, 1-self.v]
            R1 = np.stack((R1e, R1c))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        pars = {
            'Fp': ['Plasma flow',self.Fp,'mL/sec/mL'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


class ToftsSS(SteadyState):
    """Tofts tissue, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.
        - **ve** (Extravascular, extracellular volume, mL/mL): Volume fraction of the interstitial compartment.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `OneCompSS`, `PatlakSS`, `EToftsSS`, `TwoCompUptWXSS`, `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.ToftsSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 175.126 (6.654) a.u.
        Volume transfer constant (Ktrans): 0.004 (0.0) 1/sec
        Extravascular, extracellular volume (ve): 0.156 (0.015) mL/mL
        ------------------
        Derived parameters
        ------------------
        Extracellular mean transit time (Te): 39.619 sec
        Extravascular transfer constant (kep): 0.025 1/sec
    """         

    Ktrans = 0.003
    ve = 0.2
    water_exchange = True
    free = ['Ktrans','ve']
    bounds = (0, [np.inf, 1])

    def conc(self)->np.ndarray:
        """Tissue concentration.

        Returns:
            np.ndarray: Concentration in M
        """
        return dc.conc_1cm(self.ca, self.Ktrans, self.ve, dt=self.dt)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc()
        if self.water_exchange:
            R1 = self.R10 + self.r1*C
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            R1e = self.R10 + self.r1*C/self.ve
            R1c = self.R10 + np.zeros(C.size)
            v = [self.ve, 1-self.ve]
            R1 = np.stack((R1e, R1c))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        pars = {
            'Ktrans': ['Volume transfer constant',self.Ktrans,'mL/sec/mL'],
            've': ['Extravascular, extracellular volume',self.ve,'mL/mL'],
            'Te': ['Extracellular mean transit time',self.ve/self.Ktrans,'sec'],
            'kep': ['Extravascular transfer constant',self.Ktrans/self.ve,'1/sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


    
class PatlakSS(SteadyState):
    """Patlak tissue in fast water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.

    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `OneCompSS`, `ToftsSS`, `EToftsSS`, `TwoCompUptWXSS`, `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.PatlakSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(sum=True), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 174.415 (5.95) a.u.
        Plasma volume (vp): 0.049 (0.004) mL/mL
        Volume transfer constant (Ktrans): 0.001 (0.0) 1/sec
    """ 

    Ktrans = 0.003
    vb = 0.1
    water_exchange = True
    free = ['Ktrans','vp']
    bounds = (0, [np.inf, 1])

    def conc(self, sum=True):
        """Tissue concentration.

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        vp = self.vb*(1-self.Hct)
        return dc.conc_patlak(self.ca, vp, self.Ktrans, dt=self.dt, sum=sum)       

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        if self.water_exchange:
            R1 = self.R10 + self.r1*(C[0,:]+C[1,:])
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            R1b = self.R10b + self.r1*C[0,:]/self.vb
            R1e = self.R10 + self.r1*C[1,:]/(1-self.vb)
            v = [self.vb, 1-self.vb]
            R1 = np.stack((R1b, R1e))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        pars = {
            'vb': ['Blood volume',self.vb,'mL/mL'],
            'vp': ['Plasma volume',self.vb*(1-self.Hct),'mL/mL'],
            'Ktrans': ['Volume transfer constant',self.Ktrans,'1/sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


class EToftsSS(SteadyState):
    """Extended Tofts tissue in fast water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

    Probably the most common modelling approach for generic tissues. The arterial concentrations are calculated by direct analytical inversion of the arterial signal 

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.
        - **ve** (Extravascular, extracellular volume, mL/mL): Volume fraction of the interstitial compartment.

    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `OneCompSS`, `PatlakSS`, `ToftsSS`, `TwoCompUptWXSS`, `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.EToftsSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1.0,
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(sum=True), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 148.41 (0.79) a.u.
        Plasma volume (vp): 0.047 (0.001) mL/mL
        Volume transfer constant (Ktrans): 0.003 (0.0) 1/sec
        Extravascular extracellular volume (ve): 0.207 (0.003) mL/mL
        ------------------
        Derived parameters
        ------------------
        Extracellular mean transit time (Te): 65.935 sec
        Extravascular transfer constant (kep): 0.015 1/sec
        Extracellular volume (v): 0.254 mL/mL
    """        

    v = 0.6
    Ktrans = 0.003
    ub = 0.3
    water_exchange = True
    free = ['Ktrans','v','ub']
    bounds = (0, [np.inf, 1, 1])

    def conc(self, sum=True):
        """Tissue concentration

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        ve = self.v*(1-self.ub)
        vp = self.v*self.ub*(1-self.Hct)
        return dc.conc_etofts(self.ca, vp, self.Ktrans, ve, dt=self.dt, sum=sum)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        if self.water_exchange:
            R1 = self.R10 + self.r1*(C[0,:]+C[1,:])
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            ve = self.v*(1-self.ub)
            vb = self.v*self.ub
            R1b = self.R10b + self.r1*C[0,:]/vb
            R1e = self.R10 + self.r1*C[1,:]/ve
            R1c = self.R10 + np.zeros(C.shape[1])
            v = [vb, ve, 1-vb-ve]
            R1 = np.stack((R1b, R1e, R1c))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        ve = self.v*(1-self.ub)
        vb = self.v*self.ub
        vp = self.v*self.ub*(1-self.Hct)
        pars = {
            'Ktrans': ['Volume transfer constant',self.Ktrans,'1/sec'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'ub': ['Blood volume fraction',self.ub,''],
            've': ['Extravascular extracellular volume',ve,'mL/mL'],
            'vb': ['Blood volume',vb,'mL/mL'],
            'vp': ['Plasma volume',vp,'mL/mL'],
            'Te': ['Extracellular mean transit time',ve/self.Ktrans,'sec'],
            'kep': ['Extravascular transfer constant',self.Ktrans/ve,'1/sec'],
            'ECV': ['Extracellular volume',vp+ve,'mL/mL'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)

    
class TwoCompUptSS(SteadyState):
    """Two-compartment uptake model (2CUM) in fast water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Flow of plasma into the plasma compartment.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **PS** (Permeability-surface area product, mL/sec/mL): volume of plasma cleared of indicator per unit time and per unit tissue.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `OneCompSS`, `PatlakSS`, `ToftsSS`, `EToftsSS`, `TwoCompExchSS`

    Example:

        Derive 2CUM model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.TwoCompUptSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(sum=True), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 171.71 (5.044) a.u.
        Plasma flow (Fp): 0.021 (0.003) mL/sec/mL
        Plasma volume (vp): 0.064 (0.005) mL/mL
        Permeability-surface area product (PS): 0.001 (0.0) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extraction fraction (E): 0.037 sec
        Volume transfer constant (Ktrans): 0.001 mL/sec/mL
        Plasma mean transit time (Tp): 2.88 sec
    """         

    Fp = 0.01
    PS = 0.003
    vb = 0.1
    water_exchange = True
    free = ['Fp','PS','vb']
    bounds = (0, [np.inf, np.inf, 1])
    
    def conc(self, sum=True):
        """Tissue concentration

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        vp = self.vb*(1-self.Hct)
        return dc.conc_2cum(self.ca, self.Fp, vp, self.PS, dt=self.dt, sum=sum)
       
    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        if self.water_exchange:
            R1 = self.R10 + self.r1*(C[0,:]+C[1,:])
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            R1b = self.R10b + self.r1*C[0,:]/self.vb
            R1e = self.R10 + self.r1*C[1,:]/(1-self.vb)
            v = [self.vb, 1-self.vb]
            R1 = np.stack((R1b, R1e))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        vp = self.vb*(1-self.Hct)
        pars = {
            'Fp':['Plasma flow',self.Fp,'mL/sec/mL'],
            'PS':['Permeability-surface area product',self.PS,'mL/sec/mL'],
            'vb':['Blood volume',self.vb,'mL/mL'], 
            'vp':['Plasma volume',vp,'mL/mL'],
            'E':['Extraction fraction',self.PS/(self.PS+self.Fp),''],
            'Ktrans':['Volume transfer constant',self.PS*self.Fp/(self.PS+self.Fp),'mL/sec/mL'],
            'Tp':['Plasma mean transit time',vp/(self.Fp+self.PS),'sec'],
            'Tb':['Blood mean transit time',vp/self.Fp,'sec'],
            'S0':['Signal scaling factor',self.S0,'a.u.'],
        }           
        return self.add_sdev(pars)


class TwoCompExchSS(SteadyState):
    """Two-compartment exchange model (2CXM) in fast water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Flow of plasma into the plasma compartment.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **PS** (Permeability-surface area product, mL/sec/mL): volume of plasma cleared of indicator per unit time and per unit tissue.
        - **ve** (Extravascular, extracellular volume, mL/mL): Volume fraction of the interstitial compartment.

    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).
        water_exchange (bool, optional): assume fast water exchange (True) or no water exchange (False). 

    See Also:
        `UptSS`, `OneCompSS`, `PatlakSS`, `ToftsSS`, `EToftsSS`, `TwoCompUptWXSS`

    Example:

        Derive 2CXM model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.TwoCompExchSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(sum=True), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 149.772 (0.073) a.u.
        Plasma flow (Fp): 0.098 (0.001) mL/sec/mL
        Plasma volume (vp): 0.051 (0.0) mL/mL
        Permeability-surface area product (PS): 0.003 (0.0) mL/sec/mL
        Extravascular extracellular volume (ve): 0.2 (0.0) mL/mL
        ------------------
        Derived parameters
        ------------------
        Extraction fraction (E): 0.03 sec
        Volume transfer constant (Ktrans): 0.003 mL/sec/mL
        Plasma mean transit time (Tp): 0.5 sec
        Extracellular mean transit time (Te): 66.718 sec
        Extracellular volume (v): 0.251 mL/mL
        Mean transit time (T): 0.002 sec
    """         

    Fp = 0.01
    PS = 0.003
    v = 0.6
    ub = 0.3
    water_exchange = True
    free = ['Fp','PS','v','ub']
    bounds = (0, [np.inf, np.inf, 1, 1])

    def conc(self, sum=True):
        """Tissue concentration

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        ve = self.v*(1-self.ub)
        vp = self.v*self.ub*(1-self.Hct)
        return dc.conc_2cxm(self.ca, self.Fp, vp, self.PS, ve, dt=self.dt, sum=sum)
  
    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        if self.water_exchange:
            R1 = self.R10 + self.r1*(C[0,:]+C[1,:])
            ydata = dc.signal_ss(R1, self.S0, self.TR, self.FA)
        else:
            vb = self.v*self.ub
            ve = self.v*(1-self.ub)
            R1b = self.R10b + self.r1*C[0,:]/vb
            R1e = self.R10 + self.r1*C[1,:]/ve
            R1c = self.R10 + np.zeros(C.shape[1])
            v = [vb, ve, 1-vb-ve]
            R1 = np.stack((R1b, R1e, R1c))
            ydata = dc.signal_ss_nex(v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        ve = self.v*(1-self.ub)
        vb = self.v*self.ub
        vp = self.v*self.ub*(1-self.Hct)
        pars = {
            'Fp': ['Plasma flow',self.Fp,'mL/sec/mL'],
            'PS': ['Permeability-surface area product',self.PS,'mL/sec/mL'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'ub': ['Blood volume fraction',self.ub,''],
            've': ['Extravascular extracellular volume',ve,'mL/mL'],
            'vb': ['Blood volume',vb,'mL/mL'],
            'vp': ['Plasma volume',vp,'mL/mL'],
            'Te': ['Extracellular mean transit time',ve/self.PS,'sec'],
            'kep': ['Extravascular transfer constant',self.PS/ve,'1/sec'],
            'ECV': ['Extracellular volume',vp+ve,'mL/mL'],
            'E': ['Extraction fraction',self.PS/(self.PS+self.Fp),''],
            'Ktrans': ['Volume transfer constant',self.PS*self.Fp/(self.PS+self.Fp),'mL/sec/mL'],
            'Tp': ['Plasma mean transit time',vp/(self.Fp+self.PS),'sec'],
            'Tb': ['Blood mean transit time',vp/self.Fp,'sec'],
            'T': ['Mean transit time',(vp+ve)/self.Fp,'sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


# Intermediate water exchange


class OneCompWXSS(SteadyState):
    """One-compartment tissue in intermediate water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Plasma flow into the compartment per unit tissue.
        - **v** (Volume of distribution, mL/mL): Volume fraction of the compartment. 
        - **PSw** (Water permeability-surface area product, mL/sec/mL): PS for water across the compartment wall.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `OneCompSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.OneCompWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 172.679 (6.628) a.u.
        Plasma flow (Fp): 0.006 (0.002) 1/sec
        Volume of distribution (v): 0.195 (0.049) mL/mL
        Water permeability-surface area product (PSw): 0.0 (2.346) mL/mL
        ------------------
        Derived parameters
        ------------------
        Extracompartmental water mean transit time (Twe): 9.412177217600262e+32 sec
        Intracompartmental water mean transit time (Twb): 2.2783889577230225e+32 sec
    """         

    Fp = 0.01
    v = 0.05
    PSw = 10
    free = ['Fp','v','PSw']
    bounds = (0, [np.inf, 1, 'PSw'])

    def conc(self)->np.ndarray:
        """Tissue concentration.

        Returns:
            np.ndarray: Concentration in M
        """
        return dc.conc_1cm(self.ca, self.Fp, self.v, dt=self.dt)
    
    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc()
        R1e = self.R10 + self.r1*C/self.v
        R1c = self.R10 + np.zeros(C.size)
        PS = np.array([[0,self.PSw],[self.PSw,0]])
        v = [self.v, 1-self.v]
        R1 = np.stack((R1e, R1c))
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        pars = {
            'Fp': ['Plasma flow',self.Fp,'mL/sec/mL'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'PSw': ['Water permeability-surface area product',self.PSw,'mL/sec/mL'],
            'Twe': ['Extracompartmental water mean transit time', (1-self.v)/self.PSw, 'sec'],
            'Twb':  ['Intracompartmental water mean transit time', self.v/self.PSw, 'sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


class ToftsWXSS(SteadyState):
    """Tofts tissue with intermediate water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.
        - **ve** (Extravascular, extracellular volume, mL/mL): Volume fraction of the interstitial compartment.
        - **PSe** (Transendothelial water permeability-surface area product, mL/sec/mL): Permeability of water across the endothelium.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `ToftsWXSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.ToftsWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 172.679 (6.628) a.u.
        Volume transfer constant (Ktrans): 0.006 (0.002) 1/sec
        Extravascular, extracellular volume (ve): 0.195 (0.049) mL/mL
        Transendothelial water PS (PSe): 0.0 (2.346) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extracellular mean transit time (Te): 33.025 sec
        Extravascular transfer constant (kep): 0.03 1/sec
        Extravascular water mean transit time (Twe): 2.2783889577230225e+32 sec
        Intravascular water mean transit time (Twb): 9.412177217600262e+32 sec
    """         

    Ktrans = 0.003
    ve = 0.2
    PSw = 10
    free = ['Ktrans','ve','PSw']
    bounds = (0, [np.inf, 1, np.inf])

    def conc(self)->np.ndarray:
        """Tissue concentration.

        Returns:
            np.ndarray: Concentration in M
        """
        return dc.conc_1cm(self.ca, self.Ktrans, self.ve, dt=self.dt)
    
    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc()
        R1e = self.R10 + self.r1*C/self.ve
        R1c = self.R10 + np.zeros(C.size)
        PS = np.array([[0,self.PSw],[self.PSw,0]])
        v = [self.ve, 1-self.ve]
        R1 = np.stack((R1e, R1c))
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        pars = {
            'Ktrans': ['Volume transfer constant',self.Ktrans,'mL/sec/mL'],
            've': ['Extravascular, extracellular volume',self.ve,'mL/mL'],
            'Te': ['Extracellular mean transit time',self.ve/self.Ktrans,'sec'],
            'kep': ['Extravascular transfer constant',self.Ktrans/self.ve,'1/sec'],
            'PSw': ['Transendothelial water PS',self.PSw,'mL/sec/mL'],
            'Twe': ['Extravascular water mean transit time', self.ve/self.PSw, 'sec'],
            'Twb': ['Intravascular water mean transit time', (1-self.ve)/self.PSw, 'sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)


class PatlakWXSS(SteadyState):
    """Patlak tissue with intermediate exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.
        - **PSe** (Transendothelial water permeability-surface area product, mL/sec/mL): PS for water across the endothelium.

    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `PatlakSS`.

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.PatlakWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 165.529 (5.377) a.u.
        Plasma volume (vp): 0.091 (0.014) mL/mL
        Volume transfer constant (Ktrans): 0.001 (0.0) 1/sec
        Transendothelial water PS (PSe): 0.0 (0.666) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extravascular water mean transit time (Twe): 4803607269928.271 sec
        Intravascular water mean transit time (Twb): 950667689299.263 sec
    """         

    Ktrans = 0.003
    vb = 0.05
    PSe = 10
    free = ['Ktrans','vb','PSe']
    bounds = (0, [np.inf, 1, np.inf])

    def conc(self, sum=True):
        """Tissue concentration.

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        vp = self.vb*(1-self.Hct)
        return dc.conc_patlak(self.ca, vp, self.Ktrans, dt=self.dt, sum=sum)
    
    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        R1b = self.R10b + self.r1*C[0,:]/self.vb
        R1e = self.R10 + self.r1*C[1,:]/(1-self.vb)
        PS = np.array([[0,self.PSe],[self.PSe,0]])
        v = [self.vb, 1-self.vb]
        R1 = np.stack((R1b, R1e))
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        pars = {
            'vb': ['Blood volume',self.vb,'mL/mL'],
            'vp': ['Plasma volume',self.vb*(1-self.Hct),'mL/mL'],
            'Ktrans': ['Volume transfer constant',self.Ktrans,'1/sec'],
            'PSe': ['Transendothelial water PS',self.PSe,'mL/sec/mL'],
            'Twe': ['Extravascular water mean transit time', (1-self.vb)/self.PSe, 'sec'],
            'Twb': ['Intravascular water mean transit time', self.vb/self.PSe, 'sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
        }
        return self.add_sdev(pars)



class EToftsWXSS(SteadyState):
    """Extended Tofts tissue with intermediate exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): scale factor for the MR signal.
        - **vp** (Plasma volume, mL/mL): Volume fraction of the plasma compartment. 
        - **Ktrans** (Vascular transfer constant, mL/sec/mL): clearance of the plasma compartment per unit tissue.
        - **ve** (Extravascular, extracellular volume, mL/mL): Volume fraction of the interstitial compartment.
        - **PSe** (Transendothelial water permeability-surface area product, mL/sec/mL): PS for water across the endothelium.
        - **PSc** (Transcytolemmal water permeability-surface area product, mL/sec/mL): PS for water across the cell wall.

    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `EToftsSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.EToftsWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1.0,
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 149.985 (0.791) a.u.
        Plasma volume (vp): 0.046 (0.001) mL/mL
        Volume transfer constant (Ktrans): 0.003 (0.0) 1/sec
        Extravascular extracellular volume (ve): 0.205 (0.003) mL/mL
        Transendothelial water PS (PSe): 702.341 (3626.087) mL/sec/mL
        Transcytolemmal water PS (PSc): 1034.743 (5701.33) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extracellular mean transit time (Te): 65.948 sec
        Extravascular transfer constant (kep): 0.015 1/sec
        Extracellular volume (v): 0.251 mL/mL
        Intracellular water mean transit time (Twc): 0.001 sec
        Interstitial water mean transit time (Twi): 0.0 sec
        Intravascular water mean transit time (Twb): 0.0 sec
    """         

    v = 0.6
    Ktrans = 0.003
    ub = 0.3
    PSe = 10
    PSc = 10
    free = ['Ktrans','v','ub','PSe','PSc']
    bounds = (0, [np.inf, 1, 1,np.inf,np.inf])

    def conc(self, sum=True):
        """Tissue concentration.

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        ve = self.v*(1-self.ub)
        vp = self.v*self.ub*(1-self.Hct)
        return dc.conc_etofts(self.ca, vp, self.Ktrans, ve, dt=self.dt, sum=sum)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        ve = self.v*(1-self.ub)
        vb = self.v*self.ub
        R1b = self.R10b + self.r1*C[0,:]/vb
        R1e = self.R10 + self.r1*C[1,:]/ve
        R1c = self.R10 + np.zeros(C.shape[1])
        PS = np.array([[0,self.PSe,0],[self.PSe,0,self.PSc],[0,self.PSc,0]])
        v = [vb, ve, 1-vb-ve]
        R1 = np.stack((R1b, R1e, R1c))
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        ve = self.v*(1-self.ub)
        vb = self.v*self.ub
        vp = self.v*self.ub*(1-self.Hct)
        pars = {
            'Ktrans': ['Volume transfer constant',self.Ktrans,'1/sec'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'ub': ['Blood volume fraction',self.ub,''],
            've': ['Extravascular extracellular volume',ve,'mL/mL'],
            'vb': ['Blood volume',vb,'mL/mL'],
            'vp': ['Plasma volume',vp,'mL/mL'],
            'Te': ['Extracellular mean transit time',ve/self.Ktrans,'sec'],
            'kep': ['Extravascular transfer constant',self.Ktrans/ve,'1/sec'],
            'ECV': ['Extracellular volume',vp+ve,'mL/mL'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
            'PSe': ['Transendothelial water PS',self.PSe,'mL/sec/mL'],
            'PSc': ['Transcytolemmal water PS',self.PSc,'mL/sec/mL'],
            'Twc': ['Intracellular water mean transit time', (1-vb-ve)/self.PSc, 'sec'],
            'Twi': ['Interstitial water mean transit time', ve/(self.PSc+self.PSe), 'sec'],
            'Twb': [ 'Intravascular water mean transit time', vb/self.PSe, 'sec'],
        }
        return self.add_sdev(pars)


class TwoCompUptWXSS(SteadyState):
    """Two-compartment uptake model (2CUM) in intermediate water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): Scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Flow of plasma into the plasma compartment.
        - **vp** (Plasma volume): Volume fraction of the plasma compartment. 
        - **PS** (Permeability-surface area product, mL/sec/mL): Volume of plasma cleared of indicator per unit time and per unit tissue.
        - **PSe** (Transendothelial water permeability-surface area product, mL/sec/mL): PS for water across the endothelium.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec). 

    See Also:
        `TwoCompUptWXSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.TwoCompUptWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 166.214 (4.318) a.u.
        Plasma flow (Fp): 0.044 (0.009) mL/sec/mL
        Plasma volume (vp): 0.1 (0.012) mL/mL
        Permeability-surface area product (PS): 0.001 (0.0) mL/sec/mL
        Transendothelial water PS (PSe): 0.0 (0.639) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extraction fraction (E): 0.016 sec
        Volume transfer constant (Ktrans): 0.001 mL/sec/mL
        Plasma mean transit time (Tp): 2.249 sec
        Extravascular water mean transit time (Twe): 3.934327679681704e+32 sec
        Intravascular water mean transit time (Twb): 8.696123529149469e+31 sec

        **Note**: The model does not fit the data well because the no-washout assumption is invalid in this example.
    """         

    Fp = 0.01
    PS = 0.003
    vb = 0.1
    PSe = 10
    free = ['Fp','PS','vb','PSe']
    bounds = (0, [np.inf, np.inf, 1, np.inf])

    def conc(self, sum=True):
        """Tissue concentration.

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        vp = self.vb*(1-self.Hct)
        return dc.conc_2cum(self.ca, self.Fp, vp, self.PS, dt=self.dt, sum=sum)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        R1b = self.R10b + self.r1*C[0,:]/self.vb
        R1e = self.R10 + self.r1*C[1,:]/(1-self.vb)
        PS = np.array([[0,self.PSe],[self.PSe,0]])
        v = [self.vb, 1-self.vb]
        R1 = np.stack((R1b, R1e))        
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])

    def pars(self):
        vp = self.vb*(1-self.Hct)
        pars = {
            'Fp':['Plasma flow',self.Fp,'mL/sec/mL'],
            'PS':['Permeability-surface area product',self.PS,'mL/sec/mL'],
            'vb':['Blood volume',self.vb,'mL/mL'], 
            'vp':['Plasma volume',vp,'mL/mL'],
            'E':['Extraction fraction',self.PS/(self.PS+self.Fp),''],
            'Ktrans':['Volume transfer constant',self.PS*self.Fp/(self.PS+self.Fp),'mL/sec/mL'],
            'Tp':['Plasma mean transit time',vp/(self.Fp+self.PS),'sec'],
            'Tb':['Blood mean transit time',vp/self.Fp,'sec'],
            'S0':['Signal scaling factor',self.S0,'a.u.'],
            'PSe': ['Transendothelial water PS',self.PSe,'mL/sec/mL'],
            'Twe': ['Extravascular water mean transit time', (1-self.vb)/self.PSe, 'sec'],
            'Twb': ['Intravascular water mean transit time', self.vb/self.PSe, 'sec'],
        }
        return self.add_sdev(pars)  


class TwoCompExchWXSS(SteadyState):
    """Two-compartment exchange model (2CXM) in intermediate water exchange, acquired with a spoiled gradient echo sequence in steady state and using a direct inversion of the AIF.

        The free model parameters are:

        - **S0** (Signal scaling factor, a.u.): Scale factor for the MR signal.
        - **Fp** (Plasma flow, mL/sec/mL): Flow of plasma into the plasma compartment.
        - **vp** (Plasma volume): Volume fraction of the plasma compartment. 
        - **PS** (Permeability-surface area product, mL/sec/mL): Volume of plasma cleared of indicator per unit time and per unit tissue.
        - **ve** (Extravascular, extracellular volume): Volume fraction of the interstitial compartment.
        - **PSe** (Transendothelial water permeability-surface area product, mL/sec/mL): PS for water across the endothelium.
        - **PSc** (Transcytolemmal water permeability-surface area product, mL/sec/mL): PS for water across the cell wall.
    
    Args:
        aif (array-like): MRI signals measured in the arterial input.
        pars (str or array-like, optional): Either explicit array of values, or string specifying a predefined array (see the pars0 method for possible values). 
        dt (float, optional): Sampling interval of the AIF in sec. 
        Hct (float, optional): Hematocrit. 
        agent (str, optional): Contrast agent generic name.
        field_strength (float, optional): Magnetic field strength in T. 
        TR (float, optional): Repetition time, or time between excitation pulses, in sec. 
        FA (float, optional): Nominal flip angle in degrees.
        R10 (float, optional): Precontrast tissue relaxation rate in 1/sec. 
        R10b (float, optional): Precontrast arterial relaxation rate in 1/sec. 
        t0 (float, optional): Baseline length (sec).

    See Also:
        `TwoCompExchSS`

    Example:

        Derive model parameters from data.

    .. plot::
        :include-source:
        :context: close-figs
    
        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Use `make_tissue_2cm_ss` to generate synthetic test data:

        >>> time, aif, roi, gt = dc.make_tissue_2cm_ss(CNR=50)
        
        Build a tissue model and set the constants to match the experimental conditions of the synthetic test data:

        >>> model = dc.TwoCompExchWXSS(aif,
        ...     dt = time[1],
        ...     Hct = 0.45, 
        ...     agent = 'gadodiamide',
        ...     field_strength = 3.0,
        ...     TR = 0.005,
        ...     FA = 20,
        ...     R10 = 1/dc.T1(3.0,'muscle'),
        ...     R10b = 1/dc.T1(3.0,'blood'),
        ...     t0 = 15,
        ... )

        Train the model on the ROI data:

        >>> model.train(time, roi)

        Plot the reconstructed signals (left) and concentrations (right) and compare the concentrations against the noise-free ground truth:

        >>> fig, (ax0, ax1) = plt.subplots(1,2,figsize=(12,5))
        >>> #
        >>> ax0.set_title('Prediction of the MRI signals.')
        >>> ax0.plot(time/60, roi, marker='o', linestyle='None', color='cornflowerblue', label='Data')
        >>> ax0.plot(time/60, model.predict(time), linestyle='-', linewidth=3.0, color='darkblue', label='Prediction')
        >>> ax0.set_xlabel('Time (min)')
        >>> ax0.set_ylabel('MRI signal (a.u.)')
        >>> ax0.legend()
        >>> #
        >>> ax1.set_title('Reconstruction of concentrations.')
        >>> ax1.plot(gt['t']/60, 1000*gt['C'], marker='o', linestyle='None', color='cornflowerblue', label='Tissue ground truth')
        >>> ax1.plot(time/60, 1000*model.conc(), linestyle='-', linewidth=3.0, color='darkblue', label='Tissue prediction')
        >>> ax1.plot(gt['t']/60, 1000*gt['cp'], marker='o', linestyle='None', color='lightcoral', label='Arterial ground truth')
        >>> ax1.plot(time/60, 1000*model.ca, linestyle='-', linewidth=3.0, color='darkred', label='Arterial prediction')
        >>> ax1.set_xlabel('Time (min)')
        >>> ax1.set_ylabel('Concentration (mM)')
        >>> ax1.legend()
        >>> #
        >>> plt.show()

        We can also have a look at the model parameters after training:

        >>> model.print(round_to=3)
        -----------------------------------------
        Free parameters with their errors (stdev)
        -----------------------------------------
        Signal scaling factor (S0): 151.51 (0.072) a.u.
        Plasma flow (Fp): 0.097 (0.001) mL/sec/mL
        Plasma volume (vp): 0.05 (0.0) mL/mL
        Permeability-surface area product (PS): 0.003 (0.0) mL/sec/mL
        Extravascular extracellular volume (ve): 0.198 (0.0) mL/mL
        Transendothelial water PS (PSe): 1488.691 (352.238) mL/sec/mL
        Transcytolemmal water PS (PSc): 1964.363 (537.865) mL/sec/mL
        ------------------
        Derived parameters
        ------------------
        Extraction fraction (E): 0.03 sec
        Volume transfer constant (Ktrans): 0.003 mL/sec/mL
        Plasma mean transit time (Tp): 0.499 sec
        Extracellular mean transit time (Te): 66.725 sec
        Extracellular volume (v): 0.248 mL/mL
        Mean transit time (T): 2.547 sec
        Intracellular water mean transit time (Twc): 0.0 sec
        Interstitial water mean transit time (Twi): 0.0 sec
        Intravascular water mean transit time (Twb): 0.0 sec

        **Note**: fitted water PS water values are high because the simulated data are in fast water exchange.

    """         

    Fp = 0.01
    PS = 0.003
    v = 0.6
    ub = 0.3
    PSe = 10
    PSc = 10
    free = ['Fp','PS','v','ub','PSe','PSc']
    bounds = (0, [np.inf, np.inf, 1, 1,np.inf,np.inf])

    def conc(self, sum=True):
        """Tissue concentration.

        Args:
            sum (bool, optional): If True, returns the total concentrations. Else returns the concentration in the individual compartments. Defaults to True.

        Returns:
            np.ndarray: Concentration in M
        """
        ve = self.v*(1-self.ub)
        vp = self.v*self.ub*(1-self.Hct)
        return dc.conc_2cxm(self.ca, self.Fp, vp, self.PS, ve, dt=self.dt, sum=sum)

    def predict(self, xdata:np.ndarray)->np.ndarray:
        if np.amax(self.t) < np.amax(xdata):
            msg = 'The acquisition window is longer than the duration of the AIF. \n'
            msg += 'Possible solutions: (1) increase dt; (2) extend cb; (3) reduce xdata.'
            raise ValueError(msg)
        C = self.conc(sum=False)
        vb = self.v*self.ub
        ve = self.v*(1-self.ub)
        R1b = self.R10b + self.r1*C[0,:]/vb
        R1e = self.R10 + self.r1*C[1,:]/ve
        R1c = self.R10 + np.zeros(C.shape[1])
        PS = np.array([[0,self.PSe,0],[self.PSe,0,self.PSc],[0,self.PSc,0]])
        v = [vb, ve, 1-vb-ve]
        R1 = np.stack((R1b, R1e, R1c))        
        ydata = dc.signal_ss_iex(PS, v, R1, self.S0, self.TR, self.FA)
        return dc.sample(xdata, self.t, ydata, xdata[2]-xdata[1])
    
    def pars(self):
        ve = self.v*(1-self.ub)
        vb = self.v*self.ub
        vp = self.v*self.ub*(1-self.Hct)
        pars = {
            'Fp': ['Plasma flow',self.Fp,'mL/sec/mL'],
            'PS': ['Permeability-surface area product',self.PS,'mL/sec/mL'],
            'v': ['Volume of distribution',self.v,'mL/mL'],
            'ub': ['Blood volume fraction',self.ub,''],
            've': ['Extravascular extracellular volume',ve,'mL/mL'],
            'vb': ['Blood volume',vb,'mL/mL'],
            'vp': ['Plasma volume',vp,'mL/mL'],
            'Te': ['Extracellular mean transit time',ve/self.PS,'sec'],
            'kep': ['Extravascular transfer constant',self.PS/ve,'1/sec'],
            'ECV': ['Extracellular volume',vp+ve,'mL/mL'],
            'E': ['Extraction fraction',self.PS/(self.PS+self.Fp),''],
            'Ktrans': ['Volume transfer constant',self.PS*self.Fp/(self.PS+self.Fp),'mL/sec/mL'],
            'Tp': ['Plasma mean transit time',vp/(self.Fp+self.PS),'sec'],
            'Tb': ['Blood mean transit time',vp/self.Fp,'sec'],
            'T': ['Mean transit time',(vp+ve)/self.Fp,'sec'],
            'S0': ['Signal scaling factor',self.S0,'a.u.'],
            'PSe': ['Transendothelial water PS',self.PSe,'mL/sec/mL'],
            'PSc': ['Transcytolemmal water PS',self.PSc,'mL/sec/mL'],
            'Twc': ['Intracellular water mean transit time', (1-vb-ve)/self.PSc, 'sec'],
            'Twi': ['Interstitial water mean transit time', ve/(self.PSc+self.PSe), 'sec'],
            'Twb': [ 'Intravascular water mean transit time', vb/self.PSe, 'sec'],
        }
        return self.add_sdev(pars)