# -*- coding: utf-8 -*-
"""
This module contains the main class for calculating the rates of detectable gravitational waves events. The class inherits the :class:`~leLensGalaxyParameterDistribution` class for source parameters and lens parameters sampling. It also finds the image properties. :class:`~ler.LensGalaxyParameterDistribution` inherits the :class:`~ler.CBCSourceParameterDistribution`, :class:`~ler.ImageProperties` and uses `gwsnr` package for SNR calculation. 
"""

import os
import warnings
warnings.filterwarnings("ignore")
import json
import contextlib
import numpy as np
import matplotlib.pyplot as plt
from gwsnr import GWSNR
from scipy.stats import norm, gaussian_kde
from astropy.cosmology import LambdaCDM
from ..gw_source_population import CBCSourceParameterDistribution
from ..utils import append_json, get_param_from_json, batch_handler


class GWRATES(CBCSourceParameterDistribution):
    """Class to calculate both the rates of lensed and unlensed events. Please note that parameters of the simulated events are stored in json file but not as an attribute of the class. This saves RAM memory. 

    Parameters
    ----------
    npool : `int`
        number of cores to use.
        default npool = 4.
    z_min : `float`
        minimum redshift.
        default z_min = 0.
        for popI_II, popIII, primordial, BNS z_min = 0., 5., 5., 0. respectively.
    z_max : `float`
        maximum redshift.
        default z_max = 10.
        for popI_II, popIII, primordial, BNS z_max = 10., 40., 40., 2. respectively.
    size : `int`
        number of samples for sampling.
        default size = 100000.
    batch_size : `int`
        batch size for SNR calculation.
        default batch_size = 25000.
        reduce the batch size if you are getting memory error.
        recommended batch_size = 50000, if size = 1000000.
    snr_finder : `str`
        default snr_finder = 'gwsnr'.
        if 'gwsnr', the SNR will be calculated using the gwsnr package.
        if 'custom', the SNR will be calculated using a custom function.
        The custom function should have input and output as given in GWSNR.snr method.
    json_file_names: `dict`
        names of the json files to strore the necessary parameters.
        default json_file_names = {'ler_param': './LeR_params.json', 'gw_param': './gw_param.json', 'gw_param_detectable': './gw_param_detectable.json'}.\n
    kwargs : `keyword arguments`
        Note : kwargs takes input for initializing the :class:`~ler.CBCSourceParameterDistribution`, :meth:`~gwsnr_intialization`.

    Examples
    ----------
    >>> from ler.rates import GWRATES
    >>> ler = GWRATES()
    >>> ler.gw_cbc_statistics();
    >>> ler.unlensed_rate();
        
    Instance Attributes
    ----------
    LeR class has the following attributes, \n
    +-------------------------------------+----------------------------------+
    | Atrributes                          | Type                             |
    +=====================================+==================================+
    |:attr:`~z_min`                       | `float`                          |
    +-------------------------------------+----------------------------------+
    |:attr:`~z_max`                       | `float`                          |
    +-------------------------------------+----------------------------------+
    |:attr:`~event_type`                  | `str`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~cosmo`                       | `astropy.cosmology`              |
    +-------------------------------------+----------------------------------+
    |:attr:`~size`                        | `int`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~batch_size`                  | `int`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~json_file_names`             | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~directory`                   | `str`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_sampler_dict`       | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~snr_calculator_dict`         | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_json_file`          | `str`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_detectable_json_file`| `str`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param`                    | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_detectable`         | `dict`                           |
    +-------------------------------------+----------------------------------+

    Instance Methods
    ----------
    LeR class has the following methods, \n
    +-------------------------------------+----------------------------------+
    | Methods                             | Type                             |
    +=====================================+==================================+
    |:meth:`~class_initialization`        | Function to initialize the       |
    |                                     | parent classes                   |
    +-------------------------------------+----------------------------------+
    |:meth:`~gwsnr_intialization`         | Function to initialize the       |
    |                                     | gwsnr class                      |
    +-------------------------------------+----------------------------------+
    |:meth:`~snr`                         | Function to get the snr with the |
    |                                     | given parameters.                |
    +-------------------------------------+----------------------------------+
    |:meth:`~store_gwrates_params`        | Function to store the all the    |
    |                                     | necessary parameters.            |
    +-------------------------------------+----------------------------------+
    |:meth:`~gw_cbc_statistics`           | Function to generate unlensed    |
    |                                     | GW source parameters.            |
    +-------------------------------------+----------------------------------+
    |:meth:`~unlensed_sampling_routine`   | Function to generate unlensed    |
    |                                     | GW source parameters.            |
    +-------------------------------------+----------------------------------+
    |:meth:`~unlensed_rate`               | Function to calculate the        |
    |                                     | unlensed rate.                   |
    +-------------------------------------+----------------------------------+
    |:meth:`~selecting_n_gw_detectable_events`                               |
    +-------------------------------------+----------------------------------+
    |                                     | Function to select n unlensed    |
    |                                     | detectable events.               |
    +-------------------------------------+----------------------------------+
    |:meth:`~gw_param_plot`               | Function to plot the             |
    |                                     | distribution of the GW source    |
    |                                     | parameters.                      |
    +-------------------------------------+----------------------------------+
    """

    # Attributes
    z_min = None
    """``float`` \n
    Minimum redshift of the source population
    """

    z_max = None
    """``float`` \n
    Maximum redshift of the source population
    """

    event_type = None
    """``str`` \n
    Type of event to generate. \n
    e.g. 'BBH', 'BNS', 'NSBH'
    """

    cosmo = None
    """``astropy.cosmology`` \n
    Cosmology to use for the calculation.
    """

    size = None
    """``int`` \n
    Number of samples for sampling.
    """

    batch_size = None
    """``int`` \n
    Batch size for sampling.
    """

    json_file_names = None
    """``dict`` \n
    Names of the json files to strore the necessary parameters.
    """

    directory = None
    """``str`` \n
    Directory to store the interpolators.
    """

    gw_param_sampler_dict = None
    """``dict`` \n
    Dictionary of parameters to initialize the ``CBCSourceParameterDistribution`` class.
    """

    snr_calculator_dict = None
    """``dict`` \n
    Dictionary of parameters to initialize the ``GWSNR`` class.
    """

    gw_param_json_file = None
    """``str`` \n
    Json file name to store the GW source parameters.
    """

    gw_param_detectable_json_file = None
    """``str`` \n
    Json file name to store the GW source parameters of the detectable events.
    """

    def __init__(
        self,
        npool=int(4),
        z_min=0.0,
        z_max=10.0,
        event_type="BBH",
        size=100000,
        batch_size=25000,
        cosmology=None,
        snr_finder="gwsnr",
        json_file_names=None,
        directory="./interpolator_pickle",
        **kwargs,
    ):
        
        self.npool = npool
        self.z_min = z_min
        self.z_max = z_max
        self.event_type = event_type
        self.cosmo = cosmology if cosmology else LambdaCDM(H0=70, Om0=0.3, Ode0=0.7)
        self.size = size
        self.batch_size = batch_size
        self.json_file_names = json_file_names if json_file_names else dict(gwrates_param="./gwrates_params.json", gw_param="./gw_param.json", gw_param_detectable="./gw_param_detectable.json",)
        self.directory = directory

        # initialization of parent class
        self.class_initialization(params=kwargs)
        if snr_finder == "gwsnr":
            # initialization self.snr and self.pdet from GWSNR class
            self.gwsnr_intialization(params=kwargs)
        else:
            self.snr = snr_finder

        self.store_gwrates_params(json_file=self.json_file_names["gwrates_param"])

    @property
    def snr(self):
        """
        Function to get the snr with the given parameters.

        Parameters
        ----------
        gw_param_dict : `dict`
            dictionary of GW source parameters.
            mass_1 : `numpy.ndarray` or `float`
                mass_1 of the compact binary (detector frame) (Msun).
            mass_2 : `numpy.ndarray` or `float`
                mass_2 of the compact binary (detector frame) (Msun).
            luminosity_distance : `numpy.ndarray` or `float`
                luminosity distance of the source (Mpc).
            theta_jn : `numpy.ndarray` or `float`
                inclination angle of the source (rad).
            psi : `numpy.ndarray` or `float`
                polarization angle of the source (rad).
            phase : `numpy.ndarray` or `float`
                phase of GW at reference frequency  (rad).
            geocent_time : `numpy.ndarray` or `float`
                GPS time of coalescence (s).
            ra : `numpy.ndarray` or `float`
                right ascension of the source (rad).
            dec : `numpy.ndarray` or `float`
                declination of the source (rad).
            a_1 : `numpy.ndarray` or `float`
                dimensionless spin magnitude of the more massive object.
            a_2 : `numpy.ndarray` or `float`
                dimensionless spin magnitude of the less massive object.
            tilt_1 : `numpy.ndarray` or `float`
                tilt angle of the more massive object spin.
            tilt_2 : `numpy.ndarray` or `float`
                tilt angle of the less massive object spin.
            phi_12 : `numpy.ndarray` or `float`
                azimuthal angle between the two spin vectors.
            phi_jl : `numpy.ndarray` or `float`
                azimuthal angle between total angular momentum and the orbital angular momentum.

        Returns
        ----------
        optimal_snr_list : `list`
            e.g. [optimal_snr_net, 'H1', 'L1', 'V1']
            optimal_snr_net : `numpy.ndarray` or `float`
                optimal snr of the network.
            'H1' : `numpy.ndarray` or `float`
                optimal snr of H1.
            'L1' : `numpy.ndarray` or `float`
                optimal snr of L1.
            'V1' : `numpy.ndarray` or `float`
                optimal snr of V1.
        """

        return self._snr
    
    @snr.setter
    def snr(self, snr_finder):
        self._snr = snr_finder

    @property
    def gw_param(self):
        """
        Function to get data from the json file 'gw_param_json_file'.

        Returns
        ----------
        gw_param : `dict`
            dictionary of unlensed GW source parameters.
        """

        return get_param_from_json(self.gw_param_json_file)
    
    @property
    def gw_param_detectable(self):
        """
        Function to get data from the json file 'gw_param_detectable_json_file'.

        Returns
        ----------
        gw_param_detectable : `dict`
            dictionary of unlensed GW source parameters.
        """

        return get_param_from_json(self.gw_param_detectable_json_file)

    def class_initialization(self, params=None):
        """
        Function to initialize the parent classes

        Parameters
        ----------
        params : `dict`
            dictionary of parameters to initialize the parent classes
        """

        # initialization of CompactBinaryPopulation class
        # it also initializes the CBCSourceRedshiftDistribution class
        # list of relevant initialized instances,
        # 1. self.sample_source_redshift
        # 2. self.sample_gw_parameters
        input_params = dict(
            z_min=self.z_min,
            z_max=self.z_max,
            event_type=self.event_type,
            source_priors=None,
            source_priors_params=None,
            cosmology=self.cosmo,
            spin_zero=True,
            spin_precession=False,
            directory=self.directory,
            create_new_interpolator=False,
        )
        if params:
            for key, value in params.items():
                if key in input_params:
                    input_params[key] = value
        self.gw_param_sampler_dict = input_params
        # initialization of clasess
        CBCSourceParameterDistribution.__init__(
            self,
            z_min=input_params["z_min"],
            z_max=input_params["z_max"],
            event_type=input_params["event_type"],
            source_priors=input_params["source_priors"],
            source_priors_params=input_params["source_priors_params"],
            cosmology=input_params["cosmology"],
            spin_zero=input_params["spin_zero"],
            spin_precession=input_params["spin_precession"],
            directory=input_params["directory"],
            create_new_interpolator=input_params["create_new_interpolator"],
        )

    def gwsnr_intialization(self, params=None):
        """
        Function to initialize the gwsnr class

        Parameters
        ----------
        params : `dict`
            dictionary of parameters to initialize the gwsnr class
        """

        # initialization of GWSNR class
        input_params = dict(
            npool=self.npool,
            mtot_min=2.0,
            mtot_max=439.6,
            size_mtot=100,
            size_mass_ratio=50,
            sampling_frequency=2048.0,
            waveform_approximant="IMRPhenomD",
            minimum_frequency=20.0,
            snr_type="interpolation",
            waveform_inspiral_must_be_above_fmin=False,
            psds=None,
            psd_file=False,
            ifos=None,
            interpolator_dir=self.directory,
        )
        if params:
            for key, value in params.items():
                if key in input_params:
                    input_params[key] = value
        self.snr_calculator_dict = input_params
        gwsnr = GWSNR(
                    npool=input_params["npool"],
                    mtot_min=input_params["mtot_min"],
                    mtot_max=input_params["mtot_max"],
                    # nsampl_es_mtot=input_params["size_mtot"],
                    # nsampl_es_mass_ratio=input_params["size_mass_ratio"],
                    sampling_frequency=input_params["sampling_frequency"],
                    waveform_approximant=input_params["waveform_approximant"],
                    minimum_frequency=input_params["minimum_frequency"],
                    snr_type=input_params["snr_type"],
                    waveform_inspiral_must_be_above_fmin=input_params[
                        "waveform_inspiral_must_be_above_fmin"
                    ],
                    psds=input_params["psds"],
                    psd_file=input_params["psd_file"],
                    ifos=input_params["ifos"],
                    interpolator_dir=input_params["interpolator_dir"],
                )

        self.snr = gwsnr.snr
        #self.pdet = gwsnr.pdet


    def store_gwrates_params(self, json_file="./gwrates_params.json"):
        """
        Function to store the all the necessary parameters. This is useful for reproducing the results. All the parameters stored are in string format to make it json compatible.

        Parameters
        ----------
        json_file : `str`
            name of the json file to store the parameters
        """

        # store gw_param_sampler_dict, lensed_param_sampler_dict and snr_calculator_dict
        parameters_dict = dict(
            npool=str(self.npool),
            z_min=str(self.z_min),
            z_max=str(self.z_max),
            size=str(self.size),
            batch_size=str(self.batch_size),
            cosmology=str(self.cosmo),
            snr_finder=str(self.snr),
            json_file_names=str(self.json_file_names),
            directory=str(self.directory),
        )

        # cbc params
        gw_param_sampler_dict = self.gw_param_sampler_dict.copy()
        # convert all dict values to str
        for key, value in gw_param_sampler_dict.items():
            gw_param_sampler_dict[key] = str(value)
        parameters_dict.update({"gw_param_sampler_dict": gw_param_sampler_dict})

        # snr calculator params
        try:
            snr_calculator_dict = self.snr_calculator_dict.copy()
            for key, value in snr_calculator_dict.items():
                snr_calculator_dict[key] = str(value)
            parameters_dict.update({"snr_calculator_dict": snr_calculator_dict})

            file_name = json_file
            append_json(file_name, parameters_dict, replace=True)
        except:
            # if snr_calculator is custom function
            pass

    def gw_cbc_statistics(
        self, size=None, resume=False, json_file="./gw_params.json",
    ):
        """
        Function to generate unlensed GW source parameters. This function also stores the parameters in json file.

        Parameters
        ----------
        size : `int`
            number of samples.
            default size = 100000.
        resume : `bool`
            resume = False (default) or True.
            if True, the function will resume from the last batch.
        json_file : `str`
            json file name for storing the parameters.
            default json_file = './gw_params.json'.

        Returns
        ----------
        gw_param : `dict`
            dictionary of unlensed GW source parameters.
            gw_param.keys() = ['zs', 'geocent_time', 'ra', 'dec', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2', 'opt_snr_net', 'L1', 'H1', 'V1']
        """

        # gw parameter sampling
        if size is None:
            size = self.size

        # sampling in batches
        batch_handler(
            size=size,
            batch_size=self.batch_size,
            sampling_routine=self.unlensed_sampling_routine,
            json_file=json_file,
            resume=resume,
        )

        gw_param = get_param_from_json(json_file)
        self.gw_param_json_file = json_file
        return gw_param
    
    def unlensed_sampling_routine(self, size, json_file, resume=False,
    ):
        """
        Function to generate unlensed GW source parameters. This function also stores the parameters in json file.

        Parameters
        ----------
        size : `int`
            number of samples.
            default size = 100000.
        resume : `bool`
            resume = False (default) or True.
            if True, the function will resume from the last batch.
        json_file : `str`
            json file name for storing the parameters.
            default json_file = './gw_params.json'.

        Returns
        ----------
        gw_param : `dict`
            dictionary of unlensed GW source parameters.
            gw_param.keys() = ['zs', 'geocent_time', 'ra', 'dec', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2', 'opt_snr_net', 'L1', 'H1', 'V1']
        """

        # get gw params
        print("sampling gw source params...")
        gw_param = self.sample_gw_parameters(size=size)
        # Get all of the signal to noise ratios
        print("calculating snrs...")
        snrs = self.snr(gw_param_dict=gw_param)
        gw_param.update(snrs)

        # store all params in json file
        append_json(file_name=json_file, dictionary=gw_param, replace=not (resume))

    def unlensed_rate(
        self,
        gw_param="./gw_params.json",
        snr_threshold=8.0,
        jsonfile="./gw_params_detectable.json",
        detectability_condition="step_function",
    ):
        """
        Function to calculate the unlensed rate. This function also stores the parameters of the detectable events in json file.

        Parameters
        ----------
        gw_param : `dict` or `str`
            dictionary of GW source parameters or json file name.
            default gw_param = './gw_params.json'.
        snr_threshold : `float`
            threshold for detection signal to noise ratio.
            e.g. snr_threshold = 8.
        jsonfile : `str`
            json file name for storing the parameters of the detectable events.
            default jsonfile = './gw_params_detectable.json'.
        detectability_condition : `str`
            detectability condition. 
            default detectability_condition = 'step_function'.
            other options are 'pdet'.

        Returns
        ----------
        total_rate : `float`
            total unlensed rate (Mpc^-3 yr^-1).
        gw_param : `dict`
            dictionary of unlensed GW source parameters of the detectable events.
            gw_param.keys() = ['zs', 'geocent_time', 'ra', 'dec', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2', 'opt_snr_net', 'L1', 'H1', 'V1']
        """
        
        # call self.json_file_names["gwrates_param"] and for adding the final results
        with open(self.json_file_names["gwrates_param"], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # get gw params from json file if not provided
        if type(gw_param) == str:
            self.gw_param_json_file = gw_param
            print(f"getting gw_params from json file {gw_param}...")
            gw_param = get_param_from_json(gw_param)
            
        if detectability_condition == "step_function":
            param = gw_param["opt_snr_net"]
            threshold = snr_threshold

        elif detectability_condition == "pdet":
            # check if pdet is provided in gw_param dict
            if "pdet_net" in gw_param.keys():
                param = gw_param["pdet_net"]
            else:
                if "opt_snr_net" in gw_param.keys():
                    param = 1 - norm.cdf(snr_threshold - gw_param["opt_snr_net"])
                    gw_param["pdet_net"] = param
                else:
                    print("pdet or opt_snr_net not provided in gw_param dict. Exiting...")
                    return None
            threshold = 0.5

        idx_detectable = param > threshold
        # montecarlo integration
        # The total rate R = norm <Theta(rho-rhoc)>
        total_rate = self.normalization_pdf_z * np.mean(idx_detectable)
        print(f"total unlensed rate (yr^-1) (with step function): {total_rate}")

        # store all detectable params in json file
        for key, value in gw_param.items():
            gw_param[key] = value[idx_detectable]

        # store all detectable params in json file
        print(f"storing detectable unlensed params in {jsonfile}")
        append_json(jsonfile, gw_param, replace=True)
        self.gw_param_detectable_json_file = jsonfile

        # write the results
        data['detectable_gw_rate_per_year'] = total_rate
        data["detectability_condition"] = detectability_condition
        append_json(self.json_file_names["gwrates_param"], data, replace=True)
        
        return total_rate, gw_param

    def selecting_n_gw_detectable_events(
        self,
        size=100,
        batch_size=None,
        snr_threshold=8.0,
        resume=False,
        json_file="./gw_params_detectable.json",
    ):
        """
        Function to select n unlensed detectable events.

        Parameters
        ----------
        size : `int`
            number of samples to be selected.
            default size = 100.
        snr_threshold : `float`
            threshold for detection signal to noise ratio.
            e.g. snr_threshold = 8.
        resume : `bool`
            if True, it will resume the sampling from the last batch.
            default resume = False.
        json_file : `str`
            json file name for storing the parameters.
            default json_file = './gw_params_detectable.json'.

        Returns
        ----------
        param_final : `dict`
            dictionary of unlensed GW source parameters of the detectable events.
            param_final.keys() = ['zs', 'geocent_time', 'ra', 'dec', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2', 'opt_snr_net', 'L1', 'H1', 'V1']
        """

        if batch_size is None:
            batch_size = self.batch_size

        if not resume:
            n = 0  # iterator
            try:
                os.remove(json_file)
            except:
                pass
        else:
            # get sample size as nsamples from json file
            param_final = get_param_from_json(json_file)
            n = len(param_final["zs"])
            del param_final

        buffer_file = "./gw_params_buffer.json"
        print("collected number of events = ", n)
        while n < size:
            # disable print statements
            with contextlib.redirect_stdout(None):
                self.unlensed_sampling_routine(
                    size=batch_size, json_file=buffer_file, resume=False
                )

                # get unlensed params
                unlensed_param = get_param_from_json(buffer_file)

                # get snr
                snr = unlensed_param["opt_snr_net"]
                # index of detectable events
                idx = snr > snr_threshold

                # store all params in json file
                for key, value in unlensed_param.items():
                    unlensed_param[key] = value[idx]
                append_json(json_file, unlensed_param, replace=False)

                n += np.sum(idx)
            print("collected number of events = ", n)

        # trim the final param dictionary
        print(f"trmming final result to size={size}")
        param_final = get_param_from_json(json_file)
        # trim the final param dictionary, randomly, without repeating
        idx = np.random.choice(len(param_final["zs"]), size, replace=False)
        for key, value in param_final.items():
            param_final[key] = param_final[key][idx]

        # save the final param dictionary
        append_json(json_file, param_final, replace=True)

        return param_final
    
    def gw_param_plot(
            self,
            param_name="zs",
            param_dict="./gw_params.json",
            param_xlabel="source redshift",
            param_ylabel="probability density",
            param_min=None,
            param_max=None,
            figsize=(4, 4),
            kde=True,
            kde_bandwidth=0.2,
            histogram=True,
            histogram_bins=30,
    ):
        """
        Function to plot the distribution of the GW source parameters.

        Parameters
        ----------
        param_name : `str`
            name of the parameter to plot.
            default param_name = 'zs'.
        param_dict : `dict` or `str`
            dictionary of GW source parameters or json file name.
            default param_dict = './gw_params.json'.
        param_xlabel : `str`
            x-axis label.
            default param_xlabel = 'source redshift'.
        param_ylabel : `str`
            y-axis label.
            default param_ylabel = 'probability density'.
        param_min : `float`
            minimum value of the parameter.
            default param_min = None.
        param_max : `float`
            maximum value of the parameter.
            default param_max = None.
        figsize : `tuple`
            figure size.
            default figsize = (4, 4).
        kde : `bool`
            if True, kde will be plotted.
            default kde = True.
        kde_bandwidth : `float`
            bandwidth for kde.
            default kde_bandwidth = 0.2.
        histogram : `bool`
            if True, histogram will be plotted.
            default histogram = True.
        histogram_bins : `int`
            number of bins for histogram.
            default histogram_bins = 30.
        """

        # get gw params from json file if not provided
        if type(param_dict) == str:
            print(f"getting gw_params from json file {param_dict}...")
            param_dict = get_param_from_json(param_dict)

        if param_min is None:
            param_min = np.min(param_dict[param_name])
        if param_max is None:
            param_max = np.max(param_dict[param_name])

        # plot the distribution of the parameter
        plt.figure(figsize=figsize)
        if histogram:
            plt.hist(
                param_dict[param_name],
                bins=histogram_bins,
                density=True,
                histtype="step",
            )
        if kde:
            kde = gaussian_kde(param_dict[param_name], bw_method=kde_bandwidth)
            x = np.linspace(param_min, param_max, 1000)
            plt.plot(x, kde(x))
        plt.xlabel(param_xlabel)
        plt.ylabel(param_ylabel)
        plt.show()


    



