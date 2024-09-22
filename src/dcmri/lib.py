from copy import deepcopy
import sys
import pickle

import numpy as np


import dcmri.pk as pk


# filepaths need to be identified with importlib_resources
# rather than __file__ as the latter does not work at runtime 
# when the package is installed via pip install

if sys.version_info < (3, 9):
    # importlib.resources either doesn't exist or lacks the files()
    # function, so use the PyPI version:
    import importlib_resources
else:
    # importlib.resources has files(), so use that:
    import importlib.resources as importlib_resources


def fetch(dataset:str)->dict:
    """Fetch a dataset included in dcmri

    Args:
        dataset (str): name of the dataset. See below for options.

    Returns:
        dict: Data as a dictionary. 

    Notes:

        The following datasets are currently available:

        **tristan_rifampicin**

            **Background**: data are provided by the liver work package of the `TRISTAN project <https://www.imi-tristan.eu/liver>`_  which develops imaging biomarkers for drug safety assessment. The data and analysis was first presented at the ISMRM in 2024 (Min et al 2024, manuscript in press). 

            The data were acquired in the aorta and liver of 10 healthy volunteers with dynamic gadoxetate-enhanced MRI, before and after administration of a drug (rifampicin) which is known to inhibit liver function. The assessments were done on two separate visits at least 2 weeks apart. On each visit, the volunteer had two scans each with a separate contrast agent injection of a quarter dose each. the scans were separated by a gap of about 1 hour to enable gadoxetate to clear from the liver. This design was deemed necessary for reliable measurement of excretion rate when liver function was inhibited.

            The research question was to what extent rifampicin inhibits gadoxetate uptake rate from the extracellular space into the liver hepatocytes (khe, mL/min/100mL) and excretion rate from hepatocytes to bile (kbh, mL/100mL/min). 2 of the volunteers only had the baseline assessment, the other 8 volunteers completed the full study. The results showed consistent and strong inhibition of khe (95%) and kbh (40%) by rifampicin. This implies that rifampicin poses a risk of drug-drug interactions (DDI), meaning it can cause another drug to circulate in the body for far longer than expected, potentially causing harm or raising a need for dose adjustment.

            **Data format**: The fetch function returns a list of dictionaries, one per subject visit. Each dictionary contains the following items: 

            - **time1aorta**: array of signals in arbitrary units, for the aorta in the first scan.
            - **time2aorta**: array of signals in arbitrary units, for the aorta in the second scan.
            - **time1liver**: array of signals in arbitrary units, for the liver in the first scan.
            - **time2liver**: array of signals in arbitrary units, for the liver in the second scan.
            - **signal1aorta**: array of signals in arbitrary units, for the aorta in the first scan.
            - **signal2aorta**: array of signals in arbitrary units, for the aorta in the second scan.
            - **signal1liver**: array of signals in arbitrary units, for the liver in the first scan.
            - **signal2liver**: array of signals in arbitrary units, for the liver in the second scan.  
            - **weight**: subject weight in kg.
            - **agent**: contrast agent generic name (str).
            - **dose**: 2-element list with contrast agent doses of first scan and second scan in mL/kg.
            - **rate**: contrast agent injection rate in mL/sec.
            - **FA**: Flip angle in degrees
            - **TR**: repretition time in sec
            - **t0**: baseline length in subject       
            - **subject**: Volunteer number. 
            - **visit**: either 'baseline' or 'rifampicin'.
            - **field_strength**: B0-field of scanner.
            - **R10b**: precontrast R1 of blood (1st scan).
            - **R10l**: precontrast R1 of liver (1st scan).
            - **R102b**:  precontrast R1 of blood (2nd scan).
            - **R102l**: precontrast R1 of liver (2nd scan).
            - **Hct**: hematocrit.
            - **vol**: liver volume in mL.
        
            Please reference the following abstract when using these data:

            Thazin Min, Marta Tibiletti, Paul Hockings, Aleksandra Galetin, Ebony Gunwhy, Gerry Kenna, Nicola Melillo, Geoff JM Parker, Gunnar Schuetz, Daniel Scotcher, John Waterton, Ian Rowe, and Steven Sourbron. *Measurement of liver function with dynamic gadoxetate-enhanced MRI: a validation study in healthy volunteers*. Proc Intl Soc Mag Reson Med, Singapore 2024.


        **tristan6drugs**

            **Background**: data are provided by the liver work package of the `TRISTAN project <https://www.imi-tristan.eu/liver>`_  which develops imaging biomarkers for drug safety assessment. The data and analysis were first published in Melillo et al (2023). 

            The study presented here measured gadoxetate uptake and excretion in healthy rats before and after injection of 6 test drugs (up to 6 rats per drug). Studies were performed in preclinical MRI scanners at 3 different centers and 2 different field strengths. 
            
            Results demonstrated that two of the tested drugs (rifampicin and cyclosporine) showed strong inhibition of both uptake and excretion. One drug (ketoconazole) inhibited uptake but not excretion. Three drugs (pioglitazone, bosentan and asunaprevir) inhibited excretion but not uptake. 

            **Data format**: The fetch function returns a list of dictionaries, one per scan. Each dictionary contains the following items: 

            - **time**: array of time points in sec
            - **spleen**: array of spleen signals in arbitrary units
            - **liver**: array of liver signals in arbitrary units.    
            - **FA**: Flip angle in degrees
            - **TR**: repretition time in sec
            - **n0**: number of precontrast acquisitions        
            - **study**: an integer identifying the substudy the scan was taken in
            - **subject**: a study-specific identifier of the subject in the range 1-6.  
            - **visit**: either 1 (baseline) or 2 (drug or vehicle/saline).
            - **center**: center wehere the study was performed, either E, G or D.
            - **field_strength**: B0-field of scanner on whuch the study was performed
            - **substance**: what was injected, eg. saline, vehicle or drug name.
            - **BAT**: Bolus arrival time
            - **duration**: duration on the injection in sec.

            Please reference the following paper when using these data:

            Melillo N, Scotcher D, Kenna JG, Green C, Hines CDG, Laitinen I, Hockings PD, Ogungbenro K, Gunwhy ER, Sourbron S, et al. Use of In Vivo Imaging and Physiologically-Based Kinetic Modelling to Predict Hepatic Transporter Mediated Drug–Drug Interactions in Rats. Pharmaceutics. 2023; 15(3):896. `[DOI] <https://doi.org/10.3390/pharmaceutics15030896>`_ 

            The data were first released as supplementary material in csv format with this paper on Zenodo. Use this DOI to reference the data themselves:

            Gunwhy, E. R., & Sourbron, S. (2023). TRISTAN-RAT (v3.0.0). `Zenodo <https://doi.org/10.5281/zenodo.8372595>`_

        **tristan_repro**

            **Background**: data are provided by the liver work package of the `TRISTAN project <https://www.imi-tristan.eu/liver>`_  which develops imaging biomarkers for drug safety assessment. The data and analysis were first published in Gunwhy et al (2024). 

            The study presented here aimed to determine the repreducibility and rpeatability of gadoxetate uptake and excretion measurements in healthy rats. Data were acquired in different centers and field strengths to identify contributing factors. Some of the studies involved repeat scans in the same subject. In some studies data on the second day were taken after adminstration of a drug (rifampicin) to test if effect sizes were reproducible.

            **Data format**: The fetch function returns a list of dictionaries, one per scan. The dictionaries in the list contain the following items: 

            - **time**: array of time points in sec
            - **spleen**: array of spleen signals in arbitrary units
            - **liver**: array of liver signals in arbitrary units.    
            - **FA**: Flip angle in degrees
            - **TR**: repretition time in sec
            - **n0**: number of precontrast acquisitions        
            - **study**: an integer identifying the substudy the scan was taken in
            - **subject**: a study-specific identifier of the subject in the range 1-6.  
            - **visit**: either 1 (baseline) or 2 (drug or vehicle/saline).
            - **center**: center wehere the study was performed, either E, G or D.
            - **field_strength**: B0-field of scanner on whuch the study was performed
            - **substance**: what was injected, eg. saline, vehicle or drug name.
            - **BAT**: Bolus arrival time
            - **duration**: duration on the injection in sec.

            Please reference the following paper when using these data:

            Ebony R. Gunwhy, Catherine D. G. Hines, Claudia Green, Iina Laitinen, Sirisha Tadimalla, Paul D. Hockings, Gunnar Schütz, J. Gerry Kenna, Steven Sourbron, and John C. Waterton. Assessment of hepatic transporter function in rats using dynamic gadoxetate-enhanced MRI: A reproducibility study. In review.

            The data were first released as supplementary material in csv format with this paper on Zenodo. Use this to reference the data themselves:

            Gunwhy, E. R., Hines, C. D. G., Green, C., Laitinen, I., Tadimalla, S., Hockings, P. D., Schütz, G., Kenna, J. G., Sourbron, S., & Waterton, J. C. (2023). Rat gadoxetate MRI signal dataset for the IMI-WP2-TRISTAN Reproducibility study [Data set]. `Zenodo. <https://doi.org/10.5281/zenodo.7838397>`_


    Example:

    Use the AortaLiver model to fit one of the **tristan_rifampicin** datasets:

    .. plot::
        :include-source:
        :context: close-figs

        >>> import dcmri as dc

        Get the data for the baseline visit of the first subject in the study:

        >>> data = dc.fetch('tristan_rifampicin')
        >>> data = data[0]

        Initialize the AortaLiver model with the available data:

        >>> model = dc.AortaLiver(
        >>>     #
        >>>     # Injection parameters
        >>>     #
        >>>     weight = data['weight'],
        >>>     agent = data['agent'],
        >>>     dose = data['dose'][0],
        >>>     rate = data['rate'],
        >>>     #
        >>>     # Acquisition parameters
        >>>     #
        >>>     field_strength = data['field_strength'],
        >>>     t0 = data['t0'],
        >>>     TR = data['TR'],
        >>>     FA = data['FA'],
        >>>     #
        >>>     # Signal parameters
        >>>     #
        >>>     R10b = data['R10b'],
        >>>     R10l = data['R10l'],
        >>>     #
        >>>     # Tissue parameters
        >>>     #
        >>>     Hct = data['Hct'],
        >>>     vol = data['volw'],
        >>> )

        We are only fitting here the first scan data, so the xdata are the aorta- and liver time points of the first scan, and the ydata are the signals at these time points:

        >>> xdata = (data['time1aorta'], data['time1liver'])
        >>> ydata = (data['signal1aorta'], data['signal1liver'])

        Train the model using these data and plot the results to check that the model has fitted the data:
        
        >>> model.train(xdata, ydata, xtol=1e-3)
        >>> model.plot(xdata, ydata)
    """


    f = importlib_resources.files('dcmri.datafiles')
    datafile = str(f.joinpath(dataset + '.pkl'))

    with open(datafile, 'rb') as fp:
        data_dict = pickle.load(fp)

    return data_dict


def influx_step(t:np.ndarray, weight:float, conc:float, dose:float, rate:float, t0:float)->np.ndarray:
    """Contrast agent flux (mmol/sec) generated by step injection.

    Args:
        t (numpy.ndarray): time points in sec where the flux is to be calculated.
        weight (float): weight of the subject in kg.
        conc (float): concentration of the contrast agent in mmol/mL.
        dose (float): injected dose in mL/kg body weight.
        rate (float): rate of contrast agent injection in mL/sec.
        t0 (float): start of the injection in sec.
        
    Raises:
        ValueError: if the injection duration is zero, or smaller than the time step of the time array.

    Returns:
        numpy.ndarray: contrast agent flux for each time point in units of mmol/sec.

    Example:

        >>> import numpy as np
        >>> import dcmri as dc

        Create an array of time points covering 20sec in steps of 1.5sec. 

        >>> t = np.arange(0, 20, 1.5)

        Inject a dose of 0.2 mL/kg bodyweight at a rate of 3mL/sec starting at t=5sec. 
        For a subject weighing 70 kg and a contrast agent with concentration 0.5M, this produces the flux:

        >>> dc.influx_step(t, 70, 0.5, 5, 0.2, 3)
        array([0. , 0. , 0. , 0. , 1.5, 1.5, 1.5, 0. , 0. , 0. , 0. , 0. , 0. ,0. ])
    """

    # Get timings
    duration = weight*dose/rate     # sec = kg * (mL/kg) / (mL/sec)
    dt = np.amin(t[1:]-t[:-1])

    # Check consistency of timings
    if dose > 0:
        if duration==0:
            msg = 'Invalid input variables. ' 
            msg += 'The injection duration is zero.'
            raise ValueError(msg)
        if dt >= duration:
            msg = 'Invalid input variables. \n' 
            msg += 'The smallest time step dt ('+str(dt)+' sec) is larger than the injection duration 1 (' + str(duration) + 'sec). \n'
            msg += 'We would recommend dt to be at least 5 times smaller.'
            raise ValueError(msg)

    # Build flux 
    Jmax = conc*rate                # mmol/sec = (mmol/ml) * (ml/sec)
    J = np.zeros(t.size)
    J[(0 < t) & (t < duration)] = Jmax
    return np.interp(t-t0, t, J, left=0)


def ca_conc(agent:str)->float:
    """Contrast agent concentration

    Args:
        agent (str): Generic contrast agent name, all lower case. Examples are 'gadobutrol', 'gadobenate', etc.

    Raises:
        ValueError: If no data are available for the agent.

    Returns:
        float: concentration in mmol/mL

    Sources: 
        - `mri questions <https://mriquestions.com/so-many-gd-agents.html>`_
        - `gadoxetate <https://www.bayer.com/sites/default/files/2020-11/primovist-pm-en.pdf>`_
        - `gadobutrol <https://www.medicines.org.uk/emc/product/2876/smpc#gref>`_

    Example:

        Print the concentration of the agents gadobutrol and gadoterate:

    .. exec_code::

        import dcmri as dc

        print('gadobutrol is available in a solution of', dc.ca_conc('gadobutrol'), 'M')
        print('gadoterate is available in a solution of', dc.ca_conc('gadoterate'), 'M')
    """    
    if agent == 'gadoxetate':
        return 0.25     # mmol/mL
    if agent == 'gadobutrol':
        return 1.0      # mmol/mL
    if agent in [
            'gadopentetate',
            'gadobenate',
            'gadodiamide',
            'gadoterate',
            'gadoteridol',
            'gadopiclenol',
        ]:
        return 0.5  # mmol/mL 
    raise ValueError('No concentration data for contrast agent ' + agent)


def ca_std_dose(agent:str)->float:
    """Standard injection volume (dose) in mL per kg body weight.

    Args:
        agent (str): Generic contrast agent name, all lower case. Examples are 'gadobutrol', 'gadobenate', etc.

    Raises:
        ValueError: If no data are available for the agent.

    Returns:
        float: Standard injection volume in mL/kg.

    Note:

        Available agents:
            - gadoxetate
            - gadobutrol
            - gadopiclenol
            - gadopentetate
            - gadobenate
            - gadodiamide
            - gadoterate
            - gadoteridol

        Sources: 
            - `mri questions <https://mriquestions.com/so-many-gd-agents.html>`_
            - `gadoxetate <https://www.bayer.com/sites/default/files/2020-11/primovist-pm-en.pdf>`_
            - `gadobutrol <https://www.medicines.org.uk/emc/product/2876/smpc#gref>`_

    Example:

        >>> import dcmri as dc
        >>> print('The standard clinical dose of gadobutrol is', dc.ca_std_dose('gadobutrol'), 'mL/kg')
        The standard clinical dose of gadobutrol is 0.1 mL/kg
    """    
    #"""Standard dose in mL/kg""" # better in mmol/kg, or offer it as an option
    if agent == 'gadoxetate':
        # https://www.bayer.com/sites/default/files/2020-11/primovist-pm-en.pdf
        return 0.1  # mL/kg
    if agent == 'gadobutrol':
        return 0.1      # mL/kg
    if agent == 'gadopiclenol':
        return 0.1      # mL/kg
    if agent in [
            'gadopentetate',
            'gadobenate',
            'gadodiamide',
            'gadoterate',
            'gadoteridol',
            ]:
        return 0.2      # mL/kg  # 0.5 mmol/mL = 0.1 mmol/kg
    raise ValueError('No dosage data for contrast agent ' + agent)


def relaxivity(field_strength=3.0, tissue='plasma', agent='gadoxetate', type='T1')->float: 
    """Contrast agent relaxivity values in units of Hz/M

    Args:
        field_strength (float, optional): Field strength in Tesla. Defaults to 3.0.
        tissue (str, optional): Tissue type - options are 'plasma', 'hepatocytes'. Defaults to 'plasma'.
        agent (str, optional): Generic contrast agent name, all lower case. Examples are 'gadobutrol', 'gadobenate', etc.. Defaults to 'gadoxetate'.
        type (str, optional): transverse (T2 or T2*) or longitudinal (T1) relaxivity. Defaults to 'T1'.

    Returns:
        float: relaxivity in Hz/M or 1/(sec*M)

    Note:

        This library is in construction and not all known values are currently available through this function.

        Available contrasts:
            - T1

        Available tissues:
            - blood
            - plasma
            - hepatocytes

        Available agents:
            - gadopentetate
            - gadobutrol
            - gadoteridol
            - gadobenade
            - gadoterate
            - gadodiamide
            - mangafodipir
            - gadoversetamide
            - ferucarbotran
            - ferumoxide
            - gadoxetate

        Available field strengths:
            - 0.47
            - 1.5
            - 3
            - 4.7
            - 7.0 (gadoxetate)
            - 9.0 (gadoxetate)

        Sources: 
            - Rohrer M, et al. Comparison of Magnetic Properties of MRI Contrast Media Solutions at Different Magnetic Field Strengths. Investigative Radiology 40(11):p 715-724, November 2005. DOI: `10.1097/01.rli.0000184756.66360.d3 <https://journals.lww.com/investigativeradiology/FullText/2005/11000/Comparison_of_Magnetic_Properties_of_MRI_Contrast.5.aspx>`_
            - Szomolanyi P, et al. Comparison of the Relaxivities of Macrocyclic Gadolinium-Based Contrast Agents in Human Plasma at 1.5, 3, and 7 T, and Blood at 3 T. Invest Radiol. 2019 Sep;54(9):559-564. doi: `10.1097/RLI.0000000000000577 <https://pubmed.ncbi.nlm.nih.gov/31124800/>`_

    Example:

        >>> import dcmri as dc
        >>> print('The plasma relaxivity of gadobutrol at 3T is', 1e-3*dc.relaxivity(3.0, 'plasma', 'gadobutrol'), 'Hz/mM')
        The plasma relaxivity of gadobutrol at 3T is 5.0 Hz/mM    
    """    
    # Blood and plasma have (theoretically) the same relaxivity
    if tissue == 'blood':
        tissue = 'plasma'
    rel = {}
    rel['T1'] = {
        'plasma': {
            'gadopentetate':{ #Magnevist
                0.47: 3.8, 
                1.5: 4.1,
                3.0: 3.7,
                4.7: 3.8,
            },
            'gadobutrol': { # Gadovist
                0.47: 6.1, 
                1.5: 5.2,
                3.0: 5.0,
                4.7: 4.7,
            },
            'gadoteridol': { #Prohance
                0.47: 4.8, 
                1.5: 4.1,
                3.0: 3.7,
                4.7: 3.7,
            },
            'gadobenade': { #Multihance
                0.47: 9.2, 
                1.5: 6.3,
                3.0: 5.5,
                4.7: 5.2,
            },
            'gadoterate': { # Dotarem
                0.47: 4.3, 
                1.5: 3.6,
                3.0: 3.5,
                4.7: 3.3,
            },
            'gadodiamide': { #Omniscan
                0.47: 4.4, 
                1.0: 4.35, # Interpolated
                1.5: 4.3,
                3.0: 4.0,
                4.7: 3.9,
            },
            'mangafodipir': { #Teslascan
                0.47: 3.6, 
                1.5: 3.6,
                3.0: 2.7,
                4.7: 2.2,
            },
            'gadoversetamide': {#Optimark
                0.47: 5.7, 
                1.5: 4.7,
                3.0: 4.5,
                4.7: 4.4,
            },
            'ferucarbotran': { #Resovist
                0.47: 15, 
                1.5: 7.4,
                3.0: 3.3,
                4.7: 1.7,
            },
            'ferumoxide': { #Feridex
                1.5: 4.5,
                3.0: 2.7,
                4.7: 1.2,
            },
            'gadoxetate': { # Primovist
                0.47: 8.7, 
                1.5: 8.1,
                3.0: 6.4,
                4.7: 6.4,
                7.0: 6.2,
                9.0: 6.1
            },
        },
    }
    rel['T1']['hepatocytes'] = rel['T1']['plasma']
    rel['T1']['hepatocytes']['gadoxetate'] = {
        1.5: 14.6,
        3.0: 9.8,
        4.7: 7.6,
        7.0: 6.0,
        9.0: 6.1,
    }
    try:
        return 1000*rel[type][tissue][agent][field_strength]
    except:
        msg = 'No relaxivity data for ' + agent + ' at ' + str(field_strength) + ' T.'
        raise ValueError(msg)


def T1(field_strength=3.0, tissue='blood', Hct=0.45)->float:
    """T1 value of selected tissue types.

    Values are taken from literature, mostly from `Stanisz et al 2005 <https://doi.org/10.1002/mrm.20605>`_

    Args:
        field_strength (float, optional): Field strength in Tesla (see below for options). Defaults to 3.0.
        tissue (str, optional): Tissue type (see below for options). Defaults to 'blood'.
        Hct (float, optional): Hematocrit value - ignored when tissue is not blood. Defaults to 0.45.

    Raises:
        ValueError: If the requested T1 values are not available.

    Returns:
        float: T1 values in sec

    Note:

        This library is in construction and not all known values are currently available through this function.

        Available tissue types:
            - skin
            - bone marrow
            - csf
            - muscle
            - heart
            - cartilage
            - white matter
            - gray matter
            - optic nerve
            - spinal cord
            - blood
            - spleen
            - liver 
            - kidney

        Available field strengths:
            - 1.5
            - 3
            - 4.7 (spleen, liver)
            - 7.0 (spleen, liver)
            - 9.0 (spleen, liver) 

    Example:

        >>> import dcmri as dc
        >>> print('The T1 of liver at 1.5T is', 1e3*dc.T1(1.5, 'liver'), 'msec')
        The T1 of liver at 1.5T is 602.0 msec
    """    
    # H. M. Gach, C. Tanase and F. Boada, "2D & 3D Shepp-Logan Phantom Standards for MRI," 2008 19th International Conference on Systems Engineering, Las Vegas, NV, USA, 2008, pp. 521-526, doi: 10.1109/ICSEng.2008.15.
           
    T1val = {
        'skin':{  # Gach 2008 (scalp)
            1.5: 0.324*(1.5**0.137),
            3.0: 0.324*(3.0**0.137),
        },
        'bone marrow':{  # Gach 2008
            1.5: 0.533*(1.5**0.088),
            3.0: 0.533*(3.0**0.088),
        },
        'csf':{  # Gach 2008
            1.5: 4.20,
            3.0: 4.20,
        },
        'muscle':{
            1.5: 1.008,
            3.0: 1.412,  
        },
        'heart':{
            1.5: 1.030,
            3.0: 1.471,  
        },
        'cartilage':{
            1.5: 1.024,
            3.0: 1.168,  
        },
        'white matter':{
            1.5: 0.884,
            3.0: 1.084,  
        },
        'gray matter':{
            1.5: 1.124,
            3.0: 1.820,  
        },
        'optic nerve':{
            1.5: 0.815,
            3.0: 1.083,  
        },
        'spinal cord':{
            1.5: 0.745,
            3.0: 0.993,  
        },
        'blood':{
            1.0: 1.378, # Extrapolated
            1.5: 1.441,
            3.0: 1/(0.52 * Hct + 0.38),  # Lu MRM 2004
        },
        'spleen':{
            4.7: 1/0.631,
            7.0: 1/0.611,
            9.0: 1/0.600,
        },
        'liver':{
            1.5: 0.602, # liver R1 in 1/sec (Waterton 2021)
            3.0: 0.752, # liver R1 in 1/sec (Waterton 2021)
            4.7: 1/1.281, # liver R1 in 1/sec (Changed from 1.285 on 06/08/2020)
            7.0: 1/1.109,  # liver R1 in 1/sec (Changed from 0.8350 on 06/08/2020)
            9.0: 1/0.920, # per sec - liver R1 (https://doi.org/10.1007/s10334-021-00928-x)
        },
        'kidney':{
            # Reference values average over cortex and medulla from Cox et al
            # https://academic.oup.com/ndt/article/33/suppl_2/ii41/5078406
            1.0: 1.017, # Extrapolated
            1.5: (1.024+1.272)/2,
            3.0: (1.399+1.685)/2,
        },
    }  
    try:
        return T1val[tissue][field_strength]
    except:
        msg = 'No T1 values for ' + tissue + ' at ' + str(field_strength) + ' T.'
        raise ValueError(msg)
    

def T2(field_strength=3.0, tissue='gray matter')->float:
    """T2 value of selected tissue types.

    Values are taken from `Gach et al 2008 <https://ieeexplore.ieee.org/document/4616690>`_

    Args:
        field_strength (float, optional): Field strength in Tesla. Defaults to 3.0.
        tissue (str, optional): Tissue type. Defaults to 'gray matter'.

    Raises:
        ValueError: If the requested T2 values are not available.

    Returns:
        float: T2 values in sec

    Note:

        This library is in construction and not all known values are currently available through this function.

        Available tissue types:
            - skin
            - bone marrow
            - csf
            - white matter
            - gray matter

        Available field strengths:
            - 1.5
            - 3

    Example:

        >>> import dcmri as dc
        >>> print('The T2 of skin at 1.5T is', 1e3*dc.T2(1.5, 'skin'), 'msec')
        The T2 of skin at 1.5T is 70.0 msec
    """    
    # H. M. Gach, C. Tanase and F. Boada, "2D & 3D Shepp-Logan Phantom Standards for MRI," 2008 19th International Conference on Systems Engineering, Las Vegas, NV, USA, 2008, pp. 521-526, doi: 10.1109/ICSEng.2008.15.
           
    T2val = {
        'skin':{  # Gach 2008 (scalp)
            1.5: 0.07,
            3.0: 0.07,
        },
        'bone marrow':{  # Gach 2008
            1.5: 0.05,
            3.0: 0.05,
        },
        'csf':{  # Gach 2008
            1.5: 1.99,
            3.0: 1.99,
        },
        'white matter':{
            1.5: 0.08,
            3.0: 0.08,  
        },
        'gray matter':{
            1.5: 0.1,
            3.0: 0.1,  
        },
    }  
    try:
        return T2val[tissue][field_strength]
    except:
        msg = 'No T2 values for ' + tissue + ' at ' + str(field_strength) + ' T.'
        raise ValueError(msg)
    

def PD(tissue='gray matter')->float:
    """Relative proton density (PD) value of selected tissue types.

    Values are taken from `Gach et al 2008 <https://ieeexplore.ieee.org/document/4616690>`_

    Args:
        tissue (str, optional): Tissue type. Defaults to 'gray matter'.

    Raises:
        ValueError: If the requested PD values are not available.

    Returns:
        float: PD values (dimensionless, range 0-1)

    Note:

        This library is in construction and not all known values are currently available through this function.

        Available tissue types:
            - skin
            - bone marrow
            - csf
            - white matter
            - gray matter

    Example:

        >>> import dcmri as dc
        >>> print('The PD of skin is', dc.PD('skin'))
        The PD of skin is 0.8
    """    
    # H. M. Gach, C. Tanase and F. Boada, "2D & 3D Shepp-Logan Phantom Standards for MRI," 2008 19th International Conference on Systems Engineering, Las Vegas, NV, USA, 2008, pp. 521-526, doi: 10.1109/ICSEng.2008.15.
           
    PDval = {
        'skin':0.8,
        'bone marrow':0.12,
        'csf':0.98,
        'white matter':0.617,
        'gray matter':0.745,
    }  
    try:
        return PDval[tissue]
    except:
        msg = 'No PD values for ' + tissue
        raise ValueError(msg)
    

def perfusion(parameter='BF', tissue='gray matter')->float:
    """perfusion parameters of selected tissue types.

    Args:
        parameter (str, optional): perfusion parameter. Options are 'BF' (blood flow), 'BV' (Blood volume), 'PS' (permeability-surface area product) and 'IV' (interstitial volume). Defaults to 'BF'.
        tissue (str, optional): Tissue type. Defaults to 'gray matter'.

    Raises:
        ValueError: If the requested parameter values are not available.

    Returns:
        float: parameter value in standard units

    Note:

        This library is in construction and not all known values are currently available through this function.

        Available tissue types:
            - skin
            - bone marrow
            - csf
            - white matter
            - gray matter

    Example:

        >>> import dcmri as dc
        >>> print('The BF of gray matter is', dc.perfusion('BF', 'gray matter'), 'mL/sec/mL')
        The BF of gray matter is 0.01 mL/sec/mL
    """  
    if parameter=='BF':      
        val = {
            'skin':0.005, # 5 kg/s/m**3 = 5000mL/sec/100*100*100 mL = 0.005mL/sec/mL
            'bone marrow':0.0013, # 0.08 ml/ml/min 
            'csf':0.0,
            'white matter':0.0033,
            'gray matter':0.01,
        }  
    elif parameter=='BV':
        val = {
            'skin':0.03, 
            'bone marrow':0.25, 
            'csf':0.0,
            'white matter':0.02,
            'gray matter':0.05,
        } 
    elif parameter=='PS': # Needs verification
        val = {
            'skin':0.001, 
            'bone marrow':0.0002, 
            'csf':0.0,
            'white matter':0.0,
            'gray matter':0.0,
        }
    elif parameter=='IV': # Needs verification
        val = {
            'skin':0.03, 
            'bone marrow':0.2, 
            'csf':0.0,
            'white matter':0.3,
            'gray matter':0.35,
        }
    try:
        return val[tissue]
    except:
        msg = 'No '+ parameter + ' values for ' + tissue
        raise ValueError(msg)
    
    
def _ellipse(array, center, axes, angle, value):
    n = array.shape[0]
    major = np.amax(axes)
    minor = np.amin(axes)
    c = np.sqrt(major**2-minor**2)
    dx = np.cos(angle*np.pi/180)
    dy = np.sin(angle*np.pi/180)
    f1 = [center[0]+dx*c, center[1]+dy*c]
    f2 = [center[0]-dx*c, center[1]-dy*c]
    d = 2.0/n
    for i in range(n):
        for j in range(n):
            x = d*(i-(n-1)/2)
            y = d*(j-(n-1)/2)
            d1 = np.sqrt((x-f1[0])**2 + (y-f1[1])**2)
            d2 = np.sqrt((x-f2[0])**2 + (y-f2[1])**2)
            if d1+d2 <= 2*major:
                array[i,j] = value
    return array


def _shepp_logan_mask(n=256)->dict:

    mask = {}

    # Background
    array = np.ones((n,n)).astype(np.bool)
    array = _ellipse(array, [0, 0], [0.72, 0.95], 0, 0)
    mask['background'] = np.flip(array, axis=0)
    
    # 1 Scalp
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0, 0], [0.72, 0.95], 0, 1)
    array = _ellipse(array, [0, 0], [0.69, 0.92], 0, 0)
    mask['scalp'] = np.flip(array, axis=0)

    # 2 Bone and marrow
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0, 0], [0.69, 0.92], 0, 1)
    array = _ellipse(array, [-0.0184,0], [0.6624, 0.874], 0, 0)
    mask['bone'] = np.flip(array, axis=0)

    # 3 CSF
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.0184,0], [0.6624, 0.874], 0, 1)
    array = _ellipse(array, [-0.0184,0], [0.6524, 0.864], 0, 0)
    mask['CSF skull'] = np.flip(array, axis=0)

    # 4 Gray matter
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.0184,0], [0.6524, 0.864], 0, 1)
    array = _ellipse(array, [0,-0.22], [0.41, 0.16], 180-18, 0)
    array = _ellipse(array, [0,0.22], [0.31, 0.11], 180+18, 0)
    array = _ellipse(array, [0.35,0], [0.21, 0.25], 0, 0)
    array = _ellipse(array, [0.1,0], [0.046, 0.046], 0, 0)
    array = _ellipse(array, [-0.605,-0.08], [0.046, 0.023], 90, 0)
    array = _ellipse(array, [-0.605,0.06], [0.023, 0.046], 0, 0)
    array = _ellipse(array, [-0.1,0.0], [0.046, 0.046], 0, 0)
    array = _ellipse(array, [-0.605,0.0], [0.023, 0.023], 0, 0)
    array = _ellipse(array, [-0.83, 0], [0.05, 0.05], 0, 0)
    array = _ellipse(array, [0.66, 0], [0.02, 0.02], 0, 0)
    mask['gray matter'] = np.flip(array, axis=0)

    # 5 CSF
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0,-0.22], [0.41, 0.16], 180-18, 1)
    array = _ellipse(array, [0.35,0], [0.21, 0.25], 0, 0)
    array = _ellipse(array, [-0.1,0.0], [0.046, 0.046], 0, 0)
    mask['CSF right']= np.flip(array, axis=0)

    # 6 CSF
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0,0.22], [0.31, 0.11], 180+18, 1)
    mask['CSF left'] = np.flip(array, axis=0)

    # 7 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0.35,0], [0.21, 0.25], 0, 1)
    array = _ellipse(array, [0.1,0], [0.046, 0.046], 0, 0)
    mask['tumor 1'] = np.flip(array, axis=0)

    # 8 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0.1,0], [0.046, 0.046], 0, 1)
    mask['tumor 2'] = np.flip(array, axis=0)

    # 9 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.605,-0.08], [0.046, 0.023], 90, 1)
    mask['tumor 4'] = np.flip(array, axis=0)

    # 10 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.605,0.06], [0.023, 0.046], 0, 1)
    mask['tumor 6'] = np.flip(array, axis=0)

    # 11 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.1,0.0], [0.046, 0.046], 0, 1)
    mask['tumor 3'] = np.flip(array, axis=0)

    # 12 Tumor
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.605,0.0], [0.023, 0.023], 0, 1)
    mask['tumor 5'] = np.flip(array, axis=0)

    # 13 Sagittal sinus
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [-0.83, 0], [0.05, 0.05], 0, 1)
    mask['sagittal sinus'] = np.flip(array, axis=0)

    # 14 Anterior cerebral artery
    array = _ellipse(np.zeros((n,n)).astype(np.bool), [0.66, 0], [0.02, 0.02], 0, 1)
    mask['anterior artery'] = np.flip(array, axis=0)
    
    return mask


def _shepp_logan(param, n=256, B0=3)->np.ndarray:
    if param == 'PD':
        scalp = PD('skin')
        bone = PD('bone marrow')
        csf = PD('csf')
        gm = PD('gray matter')
        tumor = 0.95
        blood = 0.9
    elif param == 'T2':
        scalp = T2(B0, 'skin')
        bone = T2(B0, 'bone marrow')
        csf = T2(B0, 'csf')
        gm = T2(B0, 'gray matter')
        tumor = 0.25
        blood = 0.1
    elif param=='T1':
        scalp = T1(B0, 'skin')
        bone = T1(B0, 'bone marrow')
        csf = T1(B0, 'csf')
        gm = T1(B0, 'gray matter')
        tumor = 0.926*(B0**0.217)
        blood = T1(B0, 'blood')
    elif param=='BF':
        scalp = perfusion('BF', 'skin')
        bone = perfusion('BF', 'bone marrow')
        csf = perfusion('BF', 'csf')
        gm = perfusion('BF', 'gray matter')
        tumor = 0.02
        blood = 0
    elif param=='BV':
        scalp = perfusion('BV', 'skin')
        bone = perfusion('BV', 'bone marrow')
        csf = perfusion('BV', 'csf')
        gm = perfusion('BV', 'gray matter')
        tumor = 0.1
        blood = 1
    elif param=='PS':
        scalp = perfusion('PS', 'skin')
        bone = perfusion('PS', 'bone marrow')
        csf = perfusion('PS', 'csf')
        gm = perfusion('PS', 'gray matter')
        tumor = 0.001
        blood = 0
    elif param=='IV':
        scalp = perfusion('IV', 'skin')
        bone = perfusion('IV', 'bone marrow')
        csf = perfusion('IV', 'csf')
        gm = perfusion('IV', 'gray matter')
        tumor = 0.3
        blood = 0

    array = np.zeros((n,n)).astype(np.float64)
    # 1 Scalp
    array = _ellipse(array, [0, 0], [0.72, 0.95], 0, scalp)
    # 2 Bone and marrow
    array = _ellipse(array, [0, 0], [0.69, 0.92], 0, bone)
    # 3 CSF
    array = _ellipse(array, [-0.0184,0], [0.6624, 0.874], 0, csf)
    # 4 Gray matter
    array = _ellipse(array, [-0.0184,0], [0.6524, 0.864], 0, gm)
    # 5 CSF
    array = _ellipse(array, [0,-0.22], [0.41, 0.16], 180-18, csf)
    # 6 CSF
    array = _ellipse(array, [0,0.22], [0.31, 0.11], 180+18, csf)
    # 7 Tumor
    array = _ellipse(array, [0.35,0], [0.21, 0.25], 0, tumor)
    # 8 Tumor
    array = _ellipse(array, [0.1,0], [0.046, 0.046], 0, tumor)
    # 9 Tumor
    array = _ellipse(array, [-0.605,-0.08], [0.046, 0.023], 90, tumor)
    # 10 Tumor
    array = _ellipse(array, [-0.605,0.06], [0.023, 0.046], 0, tumor)
    # 11 Tumor
    array = _ellipse(array, [-0.1,0.0], [0.046, 0.046], 0, tumor)
    # 12 Tumor
    array = _ellipse(array, [-0.605,0.0], [0.023, 0.023], 0, tumor)
    # 13 Sagittal sinus
    array = _ellipse(array, [-0.83, 0], [0.05, 0.05], 0, blood)
    # 14 Anterior cerebral artery
    array = _ellipse(array, [0.66, 0], [0.02, 0.02], 0, blood)
    # Flip
    array = np.flip(array, axis=0)
    return array


def shepp_logan(*params, n=256, B0=3):
    """Modified Shepp-Logan phantom mimicking an axial slice through the brain.

    The phantom is based on an MRI adaptation of the Shepp-Logan phantom (Gach et al 2008), but with added features for use in a DC-MRI setting: (1) additional regions for anterior cerebral artery and sinus sagittalis; (2) additional optional contrasts blood flow (BF), blood volume (BV), permeability-surface area product (PS) and interstitial volume (IV).

    Args:
        params (str or tuple): parameter or parameters shown in the image. The options are 'PD' (proton density), 'T1', 'T2', 'BF' (blood flow), 'BV' (Blood volume), 'PS' (permeability-surface area product) and 'IV' (interstitial volume). If no parameters are provided, the function returns a dictionary with 14 masks, one for each region.
        n (int, optional): matrix size. Defaults to 256.
        B0 (int, optional): field strength in T. Defaults to 3.

    Reference:
        H. M. Gach, C. Tanase and F. Boada, "2D & 3D Shepp-Logan Phantom Standards for MRI," 2008 19th International Conference on Systems Engineering, Las Vegas, NV, USA, 2008, pp. 521-526, `doi 10.1109/ICSEng.2008.15 <https://ieeexplore.ieee.org/document/4616690>`_.

    Returns:
        numpy.array or dict: if only one parameter is provided, this returns an array. In all other conditions this returns a dictionary where keys are the parameter- or region names, and values are square arrays with image values.

    Note:
        Mask names:
            - background
            - scalp
            - bone
            - CSF skull
            - CSF left
            - CSF right
            - gray matter
            - tumor 1 to tumor 6
            - sagittal sinus
            - anterior artery

    Example:

    Generate a single contrast:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Simulate a synthetic blood flow image:

        >>> im = dc.shepp_logan('BF')

        Plot the result in units of mL/min/100mL:

        >>> fig, ax = plt.subplots(figsize=(5, 5), ncols=1)
        >>> pos = ax.imshow(6000*im, cmap='gray', vmin=0.0, vmax=80)
        >>> fig.colorbar(pos, ax=ax, label='blood flow (mL/min/100mL)')
        >>> plt.show()

    Generate multiple contrasts in one function call:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Generate the MR Shepp-Logan phantom in low resolution:

        >>> im = dc.shepp_logan('PD', 'T1', 'T2', n=64)

        Plot the result:

        >>> fig, (ax1, ax2, ax3) = plt.subplots(figsize=(12, 5), ncols=3)
        >>> ax1.imshow(im['PD'], cmap='gray')
        >>> ax2.imshow(im['T1'], cmap='gray')
        >>> ax3.imshow(im['T2'], cmap='gray')
        >>> plt.show()

    Generate masks for the different regions-of-interest:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import dcmri as dc

        Generate the MR Shepp-Logan phantom masks:

        >>> im = dc.shepp_logan(n=128)

        Plot all masks:

        >>> fig, ax = plt.subplots(figsize=(8, 8), ncols=4, nrows=4)
        >>> ax[0,0].imshow(im['background'], cmap='gray')
        >>> ax[0,1].imshow(im['scalp'], cmap='gray')
        >>> ax[0,2].imshow(im['bone'], cmap='gray')
        >>> ax[0,3].imshow(im['CSF skull'], cmap='gray')
        >>> ax[1,0].imshow(im['CSF left'], cmap='gray')
        >>> ax[1,1].imshow(im['CSF right'], cmap='gray')
        >>> ax[1,2].imshow(im['gray matter'], cmap='gray')
        >>> ax[1,3].imshow(im['tumor 1'], cmap='gray')
        >>> ax[2,0].imshow(im['tumor 2'], cmap='gray')
        >>> ax[2,1].imshow(im['tumor 3'], cmap='gray')
        >>> ax[2,2].imshow(im['tumor 4'], cmap='gray')
        >>> ax[2,3].imshow(im['tumor 5'], cmap='gray')
        >>> ax[3,0].imshow(im['tumor 6'], cmap='gray')
        >>> ax[3,1].imshow(im['sagittal sinus'], cmap='gray')
        >>> ax[3,2].imshow(im['anterior artery'], cmap='gray')
        >>> for i in range(4):
        >>>     for j in range(4):
        >>>         ax[i,j].set_yticklabels([])
        >>>         ax[i,j].set_xticklabels([])
        >>> plt.show()
    """
    if len(params) == 0:
        return _shepp_logan_mask(n=n)
    elif len(params) == 1:
        return _shepp_logan(params[0], n=n, B0=B0)
    else:
        phantom = {}
        for p in params:
            phantom[p] = _shepp_logan(p, n=n, B0=B0)
        return phantom


def aif_parker(t, BAT:float=0.0)->np.ndarray:
    """Population AIF model as defined by `Parker et al (2006) <https://onlinelibrary.wiley.com/doi/full/10.1002/mrm.21066>`_

    Args:
        t (array_like): time points in units of sec. 
        BAT (float, optional): Time in seconds before the bolus arrives. Defaults to 0 sec (no delay). 

    Returns:
        np.ndarray: Concentrations in M for each time point in t. If t is a scalar, the return value is a scalar too.

    References:
        Adapted from a contribution by the QBI lab of the University of Manchester to the `OSIPI code repository <https://github.com/OSIPI/DCE-DSC-MRI_CodeCollection>`_. 
        
    Example:

        >>> import numpy as np
        >>> import dcmri as dc

        Create an array of time points covering 20sec in steps of 1.5sec, which rougly corresponds to the first pass of the Paeker AIF:

        >>> t = np.arange(0, 20, 1.5)

        Calculate the Parker AIF at these time points, and output the result in units of mM:

        >>> 1000*dc.aif_parker(t)
        array([0.08038467, 0.23977987, 0.63896354, 1.45093969, 
        2.75255937, 4.32881325, 5.6309778 , 6.06793854, 5.45203828,
        4.1540079 , 2.79568217, 1.81335784, 1.29063036, 1.08751679])
    """

    # Check input types
    if not np.isscalar(BAT):
        raise ValueError('BAT must be a scalar')

    # Convert from secs to units used internally (mins)
    t_offset = np.array(t)/60 - BAT/60

    #A1/(SD1*sqrt(2*PI)) * exp(-(t_offset-m1)^2/(2*var1))
    #A1 = 0.833, SD1 = 0.055, m1 = 0.171
    gaussian1 = 5.73258 * np.exp(
        -1.0 *
        (t_offset - 0.17046) * (t_offset - 0.17046) /
        (2.0 * 0.0563 * 0.0563) )
    
    #A2/(SD2*sqrt(2*PI)) * exp(-(t_offset-m2)^2/(2*var2))
    #A2 = 0.336, SD2 = 0.134, m2 = 0.364
    gaussian2 = 0.997356 * np.exp(
        -1.0 *
        (t_offset - 0.365) * (t_offset - 0.365) /
        (2.0 * 0.132 * 0.132))
    # alpha*exp(-beta*t_offset) / (1+exp(-s(t_offset-tau)))
    # alpha = 1.064, beta = 0.166, s = 37.772, tau = 0.482
    sigmoid = 1.050 * np.exp(-0.1685 * t_offset) / (1.0 + np.exp(-38.078 * (t_offset - 0.483)))

    pop_aif = gaussian1 + gaussian2 + sigmoid
    
    return pop_aif/1000 # convert to M


def aif_tristan_rat(t, BAT=4.6*60, duration=30) -> np.ndarray:
    """Population AIF model for rats measured with a standard dose of gadoxetate. 

    Args:
        t (array_like): time points in units of sec. 
        BAT (float, optional): Time in seconds before the bolus arrives. Defaults to 4.6 min. 
        duration (float, optional): Duration of the injection. Defaults to 30s.

    Returns:
        np.ndarray: Concentrations in M for each time point in t. If t is a scalar, the return value is a scalar too.

    References: 

        - Melillo N, Scotcher D, Kenna JG, Green C, Hines CDG, Laitinen I, et al. Use of In Vivo Imaging and Physiologically-Based Kinetic Modelling to Predict Hepatic Transporter Mediated Drug-Drug Interactions in Rats. `Pharmaceutics 2023;15(3):896 <https://doi.org/10.3390/pharmaceutics15030896>`_.

        - Gunwhy, E. R., & Sourbron, S. (2023). TRISTAN-RAT (v3.0.0). `Zenodo <https://doi.org/10.5281/zenodo.8372595>`_
        
    Example:

    .. plot::
        :include-source:

        >>> import matplotlib.pyplot as plt
        >>> import numpy as np
        >>> import dcmri as dc

        Create an array of time points over 30 minutes

        >>> t = np.arange(0, 30*60, 0.1)

        Generate the rat input function for these time points:

        >>> cp = dc.aif_tristan_rat(t)

        Plot the result:

        >>> plt.plot(t/60, 1000*cp, 'r-')
        >>> plt.title('TRISTAN rat AIF')
        >>> plt.xlabel('Time (min)')
        >>> plt.ylabel('Plasma concentration (mM)')
        >>> plt.show()
    """
    # Constants
    
    dose = 0.0075   # mmol

    Fb = 2.27/60    # mL/sec
                    # https://doi.org/10.1021/acs.molpharmaceut.1c00206
                    # (Changed from 3.61/60 on 07/03/2022)
                    # From Brown the cardiac output of rats is
                    # 110.4 mL/min (table 3-1) ~ 6.62L/h
                    # From table 3-4, sum of hepatic artery and portal vein
                    # blood flow is 17.4% of total cardiac output ~ 1.152 L/h
                    # Mass of liver is 9.15g, with density of 1.08 kg/L,
                    # therefore ~8.47mL
                    #  9.18g refers to the whole liver, i.e. intracellular tissue
                    # + extracellular space + blood
                    # Dividing 1.152L/h for 8.47mL we obtain ~2.27 mL/min/mL liver
                    # Calculation done with values in Table S2 of our article
                    # lead to the same results
    Hct = 0.418     # Cremer et al, J Cereb Blood Flow Metab 3, 254-256 (1983)
    VL = 8.47       # mL 
                    # Scotcher et al 2021, DOI: 10.1021/acs.molpharmaceut.1c00206
                    # Supplementary material, Table S2
    GFR = 1.38/60   # mL/sec (=1.38mL/min) 
                    # https://doi.org/10.1152/ajprenal.1985.248.5.F734
    P = 0.172       # mL/sec
                    # Estimated from rat repro study data using PBPK model
                    # 0.62 L/h
                    # Table 3 in Scotcher et al 2021
                    # DOI: 10.1021/acs.molpharmaceut.1c00206
    VB = 15.8       # mL 
                    # 0.06 X BW + 0.77, Assuming body weight (BW) = 250 g
                    # Lee and Blaufox. Blood volume in the rat.
                    # J Nucl Med. 1985 Jan;26(1):72-6.
    VE = 30         # mL 
                    # All tissues, including liver.
                    # Derived from Supplementary material, Table S2
                    # Scotcher et al 2021
                    # DOI: 10.1021/acs.molpharmaceut.1c00206
    E = 0.4         # Liver extraction fraction, estimated from TRISTAN data
                    # Using a model with free E, then median over population of controls

    # Derived constants
    VP = (1-Hct)*VB
    Fp = (1-Hct)*Fb
    K = GFR + E*Fp*VL # mL/sec
    
    # Influx in mmol/sec
    J = np.zeros(np.size(t))
    Jmax = dose/duration #mmol/sec
    J[(t > BAT) & (t < BAT + duration)] = Jmax

    # Model parameters
    TP = VP/(K + P)
    TE = VE/P
    E = P/(K+P)

    Jp = pk.flux_2cxm(J, [TP, TE], E, t)
    cp = Jp/K

    return cp


def model_props(model, vals:dict=None)->dict:
    """Properties of tissue models

    Args:
        model (str): a string either specifying a kinetic model, or a water exchange regime *and* a kinetic model separated by '-'. See below for more detail on available models.
        vals (dict, optional): By default the function returns variable names as parameters. If *vals* is provided, the function returns values rather than names of all model parameters. *vals* must be a dictionary with (parameter, value) pairs for all model parameters. Defaults to None.

    Raises:
        ValueError: If the model does not exist in the dictionary, or if a required value cannot be found.

    Returns:
        dict: models with water exchange have the following properties:

        - **params**: all free model parameters.
        - **lb**: lower bounds for all these parameters.
        - **ub**: upper bounds for all parameters.
        - **derived**: parameters that can be derived from teh free parameters.
        - **relax-params**: parameters needed to determine relaxation rates.
        - **relax-lb**: lower bounds for all these parameters.
        - **relax-ub**: upper bounds for all parameters.
        - **conc-params**: parameters needed to determine concentrations.
        - **conc-lb**: lower bounds for all these parameters.
        - **conc-ub**: upper bounds for all parameters.
        - **vol**: volume fractions of all water compartments.
        - **PSw**: water permeabilities between all water compartments.
        - **name**: long name for each parameter.
        - **unit**: units for each parameters.

        Kinetic models only have a more limited set of properties:

        - **params**: all free model parameters.
        - **lb**: lower bounds for all these parameters.
        - **ub**: upper bounds for all parameters.

        If the vals argument is provided, then **params** and **vols** are dictionaries including also the values of the parameters.

        
    Notes:

        The model is a string, either specifying a kinetic model, or a water exchange regime *and* a kinetic model separated by '-'. If a water exchange regime is not specified, the tissue is assumed to be in the fast water exchange limit. 

        Available kinetic models are: 
        
        - **2CX**: two-compartment exchange tissue. 
        - **2CU**: two-compartment uptake tissue. 
        - **HF**: high-flow tissue - also known as *extended Tofts model*, *extended Patlak model* or *general kinetic model*.
        - **HFU**: high-flow uptake tissue - also known as *Patlak model*.
        - **FX**: fast tracer exchange tissue. 
        - **NX**: no tracer exchange tissue. 
        - **U**: uptake tissue. 
        - **WV**: weakly vascularized tissue - also known as *Tofts model*. 
        
        The water exchange regimes are specified by a 2-element string with combinations of the letters 'F' (fast water exchange limit), 'R' (restricted water exchange) and 'N' (no water exchange). The first element of the string refers to the water exchange regime across the endothelium, the second is the water exchange regime across the tissue cell wall. The default option 'FF' need not be specified in the model. Examples of possible water exchange models are:

        - **RF**: Restricted water exchange across the endothelium (R) and fast exchange across the tissue cell wall (F). 
        - **NF**: No water exchange across the endothelium (N) and fast exchange across the tissue cell wall (F). 
        - **FR**: Fast water exchange across the endothelium (F) and restricted water exchange across the tissue cell wall (R). 
        - **RR**: Restricted water exchange across the endothelium (R) and tissue cell walls (R). 
        - **NN**: No water exchange across the endothelium (N) or tissue cell walls (N).

        All models are fully determined by a combination of one or more of the following parameters:

        - **Fp** (mL/sec/cm3): plasma flow.
        - **Ktrans** (mL/sec/cm3): volume transfer constant. 
        - **vp** (mL/cm3): plasma volume fraction.
        - **vb** (mL/cm3): blood volume fraction.
        - **vi** (mL/cm3): interstitial volume fraction.
        - **ve** (mL/cm3): extracellular volume fraction = vp+vi.
        - **vc** (mL/cm3): volume fraction of the tissue cells.
        - **PSe** (mL/sec/cm3): endothelial water permeability.
        - **PSc** (mL/sec/cm3): cytolemmal water permeability.

    The model parameters depend on the kinetics and on the water exchange regime. The tables below list all tissue types with water exchange regimes 'F' or 'R', their parameters and compartment volumes. 

        .. list-table:: **Tissue types in the fast water exchange limit (FF).**
            :widths: 20 35 25 30
            :header-rows: 1

            * - Tissue type
              - Parameters
              - Water volumes
              - Water permeabilities
            * - 2CX
              - (vp, vi, Fp, Ktrans)
              - 1
              - None
            * - 2CU
              - (vp, Fp, Ktrans)
              - 1
              - None
            * - HF
              - (vp, vi, Ktrans)
              - 1
              - None
            * - HFU
              - (vp, Ktrans)
              - 1
              - None
            * - FX
              - (ve, Fp)
              - 1  
              - None   
            * - NX
              - (vp, Fp)
              - 1 
              - None     
            * - U
              - (Fp, )
              - 1 
              - None     
            * - WV
              - (vi, Ktrans)
              - 1  
              - None 

              
        .. list-table:: **Tissue types with restricted endothelial water exchange (RF).** 
            :widths: 20 35 25 30
            :header-rows: 1

            * - Tissue type
              - Parameters
              - Water volumes
              - Water permeabilities
            * - RF-2CX
              - (vb, ) + (vp, vi, Fp, Ktrans)
              - (vb, 1-vb)
              - PSe
            * - RF-2CU
              - (vb, ) + (vp, Fp, Ktrans)
              - (vb, 1-vb)
              - PSe
            * - RF-HF
              - (vb, ) + (vp, vi, Ktrans)
              - (vb, 1-vb)
              - PSe
            * - RF-HFU
              - (vb, ) + (vp, Ktrans)
              - (vb, 1-vb)
              - PSe
            * - RF-FX
              - (vb, vc) + (ve, Fp)
              - (vb, 1-vb)  
              - PSe    
            * - RF-NX
              - (vb, ) + (vp, Fp)
              - (vb, 1-vb)  
              - PSe    
            * - RF-U
              - (vb, ) + (Fp, )
              - (vb, 1-vb)      
              - PSe
            * - RF-WV
              - (vi, Ktrans)
              - 1   
              - None

              
        .. list-table:: **Tissue types with restricted cytolemmal water exchange (FR).**
            :widths: 20 35 25 30
            :header-rows: 1

            * - Tissue type
              - Parameters
              - Water volumes
              - Water permeabilities
            * - FR-2CX
              - (vc, ) + (vp, vi, Fp, Ktrans)
              - (1-vc, vc)
              - PSc
            * - FR-2CU
              - (vc, ) + (vp, Fp, Ktrans)
              - (1-vc, vc)
              - PSc
            * - FR-HF
              - (vc, ) + (vp, vi, Ktrans)
              - (1-vc, vc)
              - PSc
            * - FR-HFU
              - (vc, ) + (vp, Ktrans)
              - (1-vc, vc)
              - PSc
            * - FR-FX
              - (vc, ) + (ve, Fp)
              - (1-vc, vc)  
              - PSc   
            * - FR-NX
              - (vc, ) + (vp, Fp)
              - (1-vc, vc)  
              - PSc    
            * - FR-U
              - (vc, ) + (Fp, )
              - (1-vc, vc)  
              - PSc    
            * - FR-WV
              - (vi, Ktrans)
              - (1-vc, vc)
              - PSc   

              
        .. list-table:: **Tissue types with restricted endothelial and cytolemmal water exchange (RR).** 
            :widths: 20 35 25 30
            :header-rows: 1 

            * - Tissue type
              - Parameters
              - Water volumes
              - Water permeabilities
            * - RR-2CX
              - (vc, ) + (vp, vi, Fp, Ktrans)
              - (vb, vi, vc)
              - PSe, PSc
            * - RR-2CU
              - (vb, vc, ) + (vp, Fp, Ktrans)
              - (vb, vi, vc)
              - PSe, PSc
            * - RR-HF
              - (vc, ) + (vp, vi, Ktrans)
              - (vb, vi, vc)
              - PSe, PSc
            * - RR-HFU
              - (vb, vc, ) + (vp, Ktrans)
              - (vb, vi, vc)
              - PSe, PSc
            * - RR-FX
              - (vb, vc, ) + (ve, Fp)
              - (vb, vi, vc)  
              - PSe, PSc   
            * - RR-NX
              - (vb, ) + (vp, Fp)
              - (vb, 1-vb) 
              - PSe    
            * - RR-U
              - (vb, ) + (Fp, )
              - (vb, 1-vb) 
              - PSe     
            * - RR-WV
              - (vi, Ktrans)
              - (1-vc, vc)  
              - PSc

    Example:

        >>> import dcmri as dc

        List the free parameters of a 2-compartment exchange model:

        >>> dc.model_props('2CX')['params']
        ['vp', 'vi', 'Fp', 'Ktrans']

        And their default upper bounds:

        >>> dc.model_props('2CX')['ub']
        [1, 1, inf, inf]

        The full list of free parameters of a 2-compartment uptake model with restricted transendothelial water exchange:

        >>> dc.model_props('RF-2CU')['params']
        ['PSe', 'vb', 'vp', 'Fp', 'Ktrans']

        And their upper bounds:

        >>> dc.model_props('RF-2CU')['ub']
        [inf, 1, 1, inf, inf]

        List the matrix of water exchange rates:

        >>> dc.model_props('RF-2CU')['PSw']
        [['', 'PSe'], ['PSe', '']]

        And the water compartmental volumes:

        >>> dc.model_props('RF-2CU')['volw']
        ['vb', '1-vb']

        If dictionary of values is available we can use the function to return parameter values rather than names:

        >>> vals = {'PSe':0.03, 'PSc':0.02, 'vb':0.1, 'vp':0.05, 'vi':0.3, 'vc':0.6, 'Fp':0.01, 'Ktrans':0.003}

        Let's return the water exchange rates for a 2-compartment exchange modelout endothelial water exchange and restricted cytolemmal water exchange:

        >>> dc.model_props('NR-2CX', vals)['PSw']
        array([[0.  , 0.  , 0.  ],
               [0.  , 0.  , 0.02],
               [0.  , 0.02, 0.  ]])

        >>> dc.model_props('NR-2CX', vals)['params']
        {'PSc': 0.02, 'vc': 0.6, 'vp': 0.05, 'vi': 0.3, 'Fp': 0.01, 'Ktrans': 0.003}

        The volume fractions of the water compartments:

        >>> dc.model_props('NR-2CX', vals)['volw']
        {'vb': 0.1, 'vi': 0.3, 'vc': 0.6}
    """

    kinetics = {
        '2CX': [['vp','vi','Fp','Ktrans'],[1,1,np.inf,np.inf]],
        '2CU': [['vp','Fp','Ktrans'],[1,np.inf,np.inf]],
        'HF': [['vp','vi','Ktrans'],[1,1,np.inf]],
        'HFU': [['vp','Ktrans'],[1,np.inf]],
        'FX': [['ve','Fp'],[1,np.inf]],
        'NX': [['vp','Fp'],[1,np.inf]],
        'U': [['Fp'],[np.inf]],
        'WV': [['vi','Ktrans'],[1,np.inf]],
    }

    mdl = model.split('-')
    kin = mdl[0] if len(mdl)==1 else mdl[1]
    wex = 'FF' if len(mdl)==1 else mdl[0]
    mdl = wex + '-' + kin 

    # If a specific model is required, check that it is in the list
    if kin not in kinetics:
        if mdl[0] not in ['F','N','R']:
            if mdl[1] not in ['F','N','R']:
                msg = 'Model ' + str(model) + ' is not recognized. '
                msg += 'Possible models are ' + str(list(props.keys())) + '.'
                raise ValueError(msg)

    # Default values
    props = {
        'conc-params': kinetics[kin][0],
        'conc-lb': [0]*len(kinetics[kin][0]),
        'conc-ub': kinetics[kin][1],
        'relax-params': [],
        'relax-lb': [],
        'relax-ub': [],
        'params': [],
        'lb': [],
        'ub': [],
        'derived': [],
        'volw': 1,
        'PSw': None,
    }

    # Add relaxation parameters
    if wex=='FF':
        pass
    elif wex in ['RF','NF']:
        if kin=='WV':
            pass
        elif kin=='FX':
            props['relax-params'] = ['vb','vc']
            props['relax-lb'] = [0,0]
            props['relax-ub'] = [1,1]
        else:
            props['relax-params'] = ['vb']
            props['relax-lb'] = [0]
            props['relax-ub'] = [1]
    elif wex in ['FR','FN']:
        if kin!='WV':
            props['relax-params'] = ['vc']
            props['relax-lb'] = [0]
            props['relax-ub'] = [1]
    else:
        if kin=='WV':
            pass
        elif kin in ['2CU','HFU','FX']:
            props['relax-params'] = ['vb','vc']
            props['relax-lb'] = [0,0]
            props['relax-ub'] = [1,1]
        elif kin in ['2CX','HF']:
            props['relax-params'] = ['vc']
            props['relax-lb'] = [0]
            props['relax-ub'] = [1]
        else:
            props['relax-params'] = ['vb']
            props['relax-lb'] = [0]
            props['relax-ub'] = [1]


    # Add compartment volumes
    if wex=='FF':
        pass
    elif wex in ['RF','NF']:
        if kin!='WV':
            props['volw'] = ['vb','1-vb']
    elif wex in ['FR','FN']:
        if kin=='WV':
            props['volw'] = ['vi','1-vi']
        else:
            props['volw'] = ['1-vc','vc']
    else:
        if kin=='WV':
            props['volw'] = ['vi','1-vi']
        elif kin in ['NX','U']:
            props['volw'] = ['vb','1-vb']
        else:
            props['volw'] = ['vb','vi','vc']


    # Add signal parameters
    if wex=='FF':
        pass
    elif wex == 'RF':
        if kin!='WV':
            props['params'] = ['PSe']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSe'],['PSe','']]
    elif wex == 'NF':
        if kin!='WV':
            props['PSw'] = [['',''],['','']]
    elif wex == 'FR':
        props['params'] = ['PSc']
        props['lb'] = [0]
        props['ub'] = [np.inf]
        props['PSw'] = [['','PSc'],['PSc','']]
    elif wex == 'FN':
        props['PSw'] = [['',''],['','']]
    elif wex == 'RR':
        if kin=='WV':
            props['params'] = ['PSc']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSc'],['PSc','']]
        elif kin in ['NX', 'U']:
            props['params'] = ['PSe']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSe'],['PSe','']]
        else:
            props['params'] = ['PSe','PSc']
            props['lb'] = [0,0]
            props['ub'] = [np.inf,np.inf]
            props['PSw'] = [['','PSe',''],['PSe','','PSc'],['','PSc','']]  
    elif wex == 'RN':
        if kin=='WV':
            props['PSw'] = [['',''],['','']]
        elif kin in ['NX', 'U']:
            props['params'] = ['PSe']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSe'],['PSe','']]
        else:
            props['params'] = ['PSe']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSe',''],['PSe','',''],['','','']] 
    elif wex == 'NR':
        if kin=='WV':
            props['params'] = ['PSc']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','PSc'],['PSc','']]
        elif kin in ['NX', 'U']:
            props['PSw'] = [['',''],['','']]
        else:
            props['params'] = ['PSc']
            props['lb'] = [0]
            props['ub'] = [np.inf]
            props['PSw'] = [['','',''],['','','PSc'],['','PSc','']] 
    elif wex == 'NN':
        if kin=='WV':
            props['PSw'] = [['',''],['','']]
        elif kin in ['NX', 'U']:
            props['PSw'] = [['',''],['','']]
        else:
            props['PSw'] = [['','',''],['','',''],['','','']] 

    # Concatenate param lists:
    props['params'] += props['relax-params']+props['conc-params']
    props['lb'] += props['relax-lb']+props['conc-lb']
    props['ub'] += props['relax-ub']+props['conc-ub']
    props['relax-params'] += props['conc-params']
    props['relax-lb'] += props['conc-lb']
    props['relax-ub'] += props['conc-ub']

    # Add derived
    p = props['params']
    if 'Ktrans' in p and 'Fp' in p:
        props['derived'].append('PS')
        props['derived'].append('E')
        if 'vi' in p:
            props['derived'].append('Ti')
        if 'vp' in p:
            props['derived'].append('Tp')
    if 'vp' in p and 'vi' in p:
        props['derived'].append('ve')
    if 'vp' in p and 'Fp' in p:
        props['derived'].append('vb')
    if 've' in p and 'Fp' in p:
        props['derived'].append('Te')
    elif 'vi' in p and 'vp' in p and 'Fp' in p:
        props['derived'].append('Te')
    if 'vb' in p and 'vi' in p and 'PSc' in p:
        props['derived'].append('Tcw')
    if 'vi' in p and 'PSe' in p and 'PSc' in p:
        props['derived'].append('Tiw')
    elif ('vi' in p and 'PSe' in p) and (wex[1]=='N'):
        props['derived'].append('Tiw')
    elif ('vi' in p and 'PSe' in p) and (wex[0]=='N'):
        props['derived'].append('Tiw')
    if 'vb' in p and 'PSe' in p:
        props['derived'].append('Tbw')
            
    # Add parameter name
    props['name'] = {}
    props['unit'] = {}
    p = props['params'] + props['derived']
    if 'Fp' in p:
        props['name']['Fp'] = 'Plasma flow'
        props['unit']['Fp'] = 'mL/sec/cm3'
    if 'PS' in p:
        props['name']['PS'] = 'Permeability-surface area product'
        props['unit']['PS'] = 'mL/sec/cm3'
    if 'Ktrans' in p:
        props['name']['Ktrans'] = 'Volume transfer constant'
        props['unit']['Ktrans'] = 'mL/sec/cm3'
    if 'vi' in p:
        props['name']['vi'] = 'Interstitial volume'
        props['unit']['vi'] = 'mL/cm3'
    if 'vp' in p:
        props['name']['vp'] = 'Plasma volume'
        props['unit']['vp'] = 'mL/cm3'
    if 've' in p:
        props['name']['ve'] = 'Extracellular volume'
        props['unit']['ve'] = 'mL/cm3'
    if 'Ti' in p:
        props['name']['Ti'] = 'Interstitial mean transit time'
        props['unit']['Ti'] = 'sec'
    if 'Tp' in p:
        props['name']['Tp'] = 'Plasma mean transit time'
        props['unit']['Tp'] = 'sec'
    if 'Tb' in p:
        props['name']['Tb'] = 'Blood mean transit time'
        props['unit']['Tb'] = 'sec'
    if 'Te' in p:
        props['name']['Te'] = 'Extracellular mean transit time'
        props['unit']['Te'] = 'sec'
    if 'E' in p:
        props['name']['E'] = 'Tracer extraction fraction'
        props['unit']['E'] = ''
    if 'vb' in p: 
        props['name']['vb'] = 'Blood volume'
        props['unit']['vb'] = 'mL/cm3'
    if 'PSe' in p: 
        props['name']['PSe'] = 'Transendothelial water PS'
        props['unit']['PSe'] = 'mL/sec/cm3'
    if 'PSc' in p: 
        props['name']['PSc'] = 'Transcytolemmal water PS'
        props['unit']['PSc'] = 'mL/sec/cm3'
    if 'Twc' in p: 
        props['name']['Twc'] = 'Intracellular water mean transit time'
        props['unit']['Twc'] = 'sec'
    if 'Twi' in p: 
        props['name']['Twi'] = 'Interstitial water mean transit time'
        props['unit']['Twi'] = 'sec'  
    if 'Twb' in p: 
        props['name']['Twb'] = 'Intravascular water mean transit time'
        props['unit']['Twb'] = 'sec'

 
    # Mo water exchange regime specified - conc model only
    if len(model.split('-'))==1:
        del props['conc-params'] 
        del props['conc-lb'] 
        del props['conc-ub'] 
        del props['relax-params'] 
        del props['relax-lb'] 
        del props['relax-ub'] 
        del props['volw']
        del props['PSw']
    
    # Return props or values
    if vals is None:
        return props
    else:
        return _model_vals(kin, wex, props, vals)
    

def _div(a, b):
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(b==0, 0, np.divide(a, b))
    

def _model_vals(kin, wex, props, vals):

    try:

        # params
        props['params'] = {p: vals[p] for p in props['params']} 
        if 'relax-params' in props:
            props['relax-params'] = {p: vals[p] for p in props['relax-params']}
        if 'conc-params' in props:
            props['conc-params'] = {p: vals[p] for p in props['conc-params']}

        props['derived'] = {}
        p = props['params']
        if 'Ktrans' in p and 'Fp' in p:
            props['derived']['PS'] = _div(vals['Fp']*vals['Ktrans'], vals['Fp']+vals['Ktrans'])
            props['derived']['E'] = _div(vals['Ktrans'], vals['Fp'])
            if 'vi' in p:
                props['derived']['Ti'] = _div(vals['vi'], props['derived']['PS'])
            if 'vp' in p:
                props['derived']['Tp'] = _div(vals['vp'], props['derived']['PS']+vals['Fp'])
        if 'vp' in p and 'vi' in p:
            props['derived']['ve'] = vals['vi']+vals['vp']
        if 'vp' in p and 'Fp' in p:
            props['derived']['vb'] = _div(vals['vp'], vals['Fp'])
        if 've' in p and 'Fp' in p:
            props['derived']['Te'] = _div(vals['ve'], vals['Fp'])
        elif 'vi' in p and 'vp' in p and 'Fp' in p:
            props['derived']['Te'] = _div(vals['vi']+vals['vp'], vals['Fp'])
        if 'vb' in p and 'vi' in p and 'PSc' in p:
            props['derived']['Tcw'] = _div(1-vals['vb']-vals['vi'], vals['PSc'])
        if 'vi' in p and 'PSe' in p and 'PSc' in p:
            props['derived']['Tiw'] = _div(vals['vi'], vals['PSc']+vals['PSe'])
        elif ('vi' in p and 'PSe' in p) and (wex[1]=='N'):
            props['derived']['Tiw'] = _div(vals['vi'], vals['PSe'])
        elif ('vi' in p and 'PSe' in p) and (wex[0]=='N'):
            props['derived']['Tiw'] = _div(vals['vi'], vals['PSc'])
        if 'vb' in p and 'PSe' in p:
            props['derived']['Tbw'] = _div(vals['vb'], vals['PSe'])

        # vols
        if 'volw' in props:
            if props['volw']==1:
                pass
            elif props['volw'][1]=='1-vb':
                vb=vals['vb'] if 'vb' in vals else 1-vals['vc']-vals['vi']
                props['volw'] = {'vb':vb, '1-vb':1-vb}
            elif props['volw'][0]=='1-vc':
                props['volw'] = {'1-vc':1-vals['vc'], 'vc':vals['vc']}
            elif props['volw'][1]=='1-vi':
                props['volw'] = {'vi':vals['vi'], '1-vi':1-vals['vi']}
            else:
                vb = 1-vals['vc']-vals['vi']
                props['volw'] = {'vb':vb, 'vi':vals['vi'], 'vc':vals['vc']}

         # PSw
        if 'PSw' in props:
            if props['PSw'] is None:
                pass
            else:
                n = len(props['PSw'])
                PSw = np.zeros((n,n))
                for i in range(n):
                    for j in range(n):
                        if props['PSw'][i][j] != '':
                            PSw[i,j] = vals[props['PSw'][i][j]]
                props['PSw'] = PSw

    except KeyError as err:
        msg = 'Cannot return parameter values. \n'
        msg += 'The vals dictionary provided to model_props() is missing a value for ' + str(err) + '.'
        raise ValueError(msg)

    return props






