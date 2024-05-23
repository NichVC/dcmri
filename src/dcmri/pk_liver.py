import numpy as np
import dcmri as dc

def liver_conc_pc(ca, Te, De, ve, t=None, dt=1.0):
    """Single-inlet liver model modelling the extracellular space (gut and liver) as a plug-flow compartment.

    Args:
        ca (array_like): the indicator concentration in the plasma of the feeding artery, as a 1D array, in units of M.
        Te (float, sec): mean transit time of the extracellular space.
        De (float): Transit time dispersion of the extracellular space, in the range [0,1].
        ve (float): volume faction of the extracellular space.
        t (array_like, sec, optional): the time points in sec of the input function *ca*. If *t* is not provided, the time points are assumed to be uniformly spaced with spacing *dt*. Defaults to None.
        dt (float, sec, optional): spacing in seconds between time points for uniformly spaced time points. This parameter is ignored if *t* is explicity provided. Defaults to 1.0.

    Returns:
        numpy.ndarray: If sum=True, this is a 1D array with the total concentration at each time point. If sum=False this is the concentration in each compartment, and at each time point, as a 2D array with dimensions *(2,k)*, where 2 is the number of compartments and *k* is the number of time points in *ca*. The concentration is returned in units of M.

    See Also:
        `liver_conc_pcc`, `liver_conc_pcc_ns`

    Example:

        Plot concentration in the liver for typical values:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> import dcmri as dc

        Generate a population-average input function:

        >>> t = np.arange(0, 600, 1.5)
        >>> ca = dc.aif_parker(t, BAT=20)

        Use the function to generate liver tissue concentrations:

        >>> C = dc.liver_conc_pc(ca, 20, 0.5, 0.3, t)

        Plot all concentrations:

        >>> fig, ax = plt.subplots(1,1,figsize=(6,5))
        >>> ax.set_title('Liver concentrations')
        >>> ax.plot(t/60, 1000*C, linestyle='-', linewidth=3.0, color='darkviolet', label='Whole liver')
        >>> ax.set_xlabel('Time (min)')
        >>> ax.set_ylabel('Tissue concentration (mM)')
        >>> ax.legend()
        >>> plt.show()
    """
    # Propagate through the gut
    ce = dc.flux_pfcomp(ca, Te, De, t=t, dt=dt, solver='interp')
    # Tissue concentration in the extracellular space
    Ce = ve*ce
    return Ce

    
def liver_conc_pcc(ca, Te, De, ve, khe, Th, t=None, dt=1.0, sum=True):
    """Single-inlet liver model modelling the extracellular space (gut and liver) as a plug-flow compartment and the hepatocytes as a compartment.

    Args:
        ca (array_like): the indicator concentration in the plasma of the feeding artery, as a 1D array, in units of M.
        Te (float, sec): mean transit time of the extracellular space.
        De (float): Transit time dispersion of the extracellular space, in the range [0,1].
        ve (float): volume faction of the extracellular space.
        khe (float, mL/sec/mL): rate constant for indicator transport from extracellular space to hepatocytes. 
        Th (float, sec): mean transit time of the hepatocytes.
        t (array_like, sec, optional): the time points in sec of the input function *ca*. If *t* is not provided, the time points are assumed to be uniformly spaced with spacing *dt*. Defaults to None.
        dt (float, sec, optional): spacing in seconds between time points for uniformly spaced time points. This parameter is ignored if *t* is explicity provided. Defaults to 1.0.
        sum (bool, optional): if set to True, the total concentration is returned. If set to False, the concentration in the compartments is returned separately. Defaults to True.

    Returns:
        numpy.ndarray: If sum=True, this is a 1D array with the total concentration at each time point. If sum=False this is the concentration in each compartment, and at each time point, as a 2D array with dimensions *(2,k)*, where 2 is the number of compartments and *k* is the number of time points in *ca*. The concentration is returned in units of M.

    See Also:
        `liver_conc_pcc_ns`

    Example:

        Plot concentration in the liver for typical values:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> import dcmri as dc

        Generate a population-average input function:

        >>> t = np.arange(0, 600, 1.5)
        >>> ca = dc.aif_parker(t, BAT=20)

        Use the function to generate liver tissue concentrations:

        >>> C = dc.liver_conc_pcc(ca, 20, 0.5, 0.3, 0.1, 600, t, sum=False)

        Plot all concentrations:

        >>> fig, ax = plt.subplots(1,1,figsize=(6,5))
        >>> ax.set_title('Liver concentrations')
        >>> ax.plot(t/60, 1000*C[0,:], linestyle='-', linewidth=3.0, color='darkblue', label='Extracellular')
        >>> ax.plot(t/60, 1000*C[1,:], linestyle='--', linewidth=3.0, color='darkgreen', label='Hepatocytes')
        >>> ax.plot(t/60, 1000*(C[0,:]+C[1,:]), linestyle='-.', linewidth=3.0, color='darkviolet', label='Whole liver')
        >>> ax.set_xlabel('Time (min)')
        >>> ax.set_ylabel('Tissue concentration (mM)')
        >>> ax.legend()
        >>> plt.show()
    """

    # Propagate through the gut
    ce = dc.flux_pfcomp(ca, Te, De, t=t, dt=dt, solver='interp')
    # Tissue concentration in the extracellular space
    Ce = ve*ce
    # Tissue concentration in the hepatocytes
    Ch = dc.conc_comp(khe*ca, Th, t=t, dt=dt) 
    if sum:
        return Ce+Ch
    else:
        return np.stack((Ce,Ch))
    

def liver_conc_pcc_ns(ca, Te, De, ve, khe, Th, t=None, dt=1.0, sum=True):
    """Single-inlet liver model modelling the extracellular space (gut and liver) as a plug-flow compartment and the hepatocytes as a non-stationary compartment.

    Args:
        ca (array_like): the indicator concentration in the plasma of the feeding artery, as a 1D array, in units of M.
        Te (float, sec): mean transit time of the extracellular space.
        De (float): Transit time dispersion of the extracellular space, in the range [0,1].
        ve (float): volume faction of the extracellular space.
        khe (array-like, mL/sec/mL): array of rate constants for indicator transport from extracellular space to hepatocytes. 
        Th (array-like, sec): array of mean transit times of the hepatocytes.
        t (array_like, sec, optional): the time points in sec of the input function *ca*. If *t* is not provided, the time points are assumed to be uniformly spaced with spacing *dt*. Defaults to None.
        dt (float, sec, optional): spacing in seconds between time points for uniformly spaced time points. This parameter is ignored if *t* is explicity provided. Defaults to 1.0.
        sum (bool, optional): if set to True, the total concentration is returned. If set to False, the concentration in the compartments is returned separately. Defaults to True.

    Returns:
        numpy.ndarray: If sum=True, this is a 1D array with the total concentration at each time point. If sum=False this is the concentration in each compartment, and at each time point, as a 2D array with dimensions *(2,k)*, where 2 is the number of compartments and *k* is the number of time points in *ca*. The concentration is returned in units of M.

    See Also:
        `liver_conc_pcc`

    Example:

        Plot concentration in the liver for typical values:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> import dcmri as dc

        Generate a population-average input function:

        >>> t = np.arange(0, 1200, 1.5)
        >>> ca = dc.aif_parker(t, BAT=20)

        In this case we can allow the function to change over the duration of the scan. Lets assume that the uptake and excretion functions are both inhibited at the start of the scan, and recover to normal values towards the end:

        >>> khe = [0.01,0.2]
        >>> Th = [1800, 300]

        Use the function to generate liver tissue concentrations:

        >>> C = dc.liver_conc_pcc_ns(ca, 20, 0.5, 0.3, khe, Th, t, sum=False)

        Plot all concentrations:

        >>> fig, ax = plt.subplots(1,1,figsize=(6,5))
        >>> ax.set_title('Liver concentrations')
        >>> ax.plot(t/60, 1000*C[0,:], linestyle='-', linewidth=3.0, color='darkblue', label='Extracellular')
        >>> ax.plot(t/60, 1000*C[1,:], linestyle='--', linewidth=3.0, color='darkgreen', label='Hepatocytes')
        >>> ax.plot(t/60, 1000*(C[0,:]+C[1,:]), linestyle='-.', linewidth=3.0, color='darkviolet', label='Whole liver')
        >>> ax.set_xlabel('Time (min)')
        >>> ax.set_ylabel('Tissue concentration (mM)')
        >>> ax.legend()
        >>> plt.show()
    """
    khe_i = dc.interp(khe, t)
    Th_i = dc.interp(Th, t)
    # Propagate through the gut
    ce = dc.flux_pfcomp(ca, Te, De, t=t, dt=dt, solver='interp')
    # Tissue concentration in the extracellular space
    Ce = ve*ce
    # Tissue concentration in the hepatocytes
    Ch = dc.conc_nscomp(khe_i*ca, Th_i, t=t, dt=dt)
    if sum:
        return Ce+Ch
    else:
        return np.stack((Ce,Ch))

