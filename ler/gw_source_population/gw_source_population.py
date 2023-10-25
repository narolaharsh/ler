# -*- coding: utf-8 -*-
"""
This module contains the classes to generate source galaxy population model
and compact binary population model. The compact binary population model
inherits from the source galaxy population model. The source galaxy population
model is used to generate the source galaxy population model. The compact binary
population model is used to generate the compact binary population model.
"""

import warnings

warnings.filterwarnings("ignore")
import numpy as np

# import pycbc
import bilby

# from scipy.stats import randint

# from gwcosmo import priors as p
from scipy.interpolate import interp1d
from scipy.integrate import quad

# for redshift to luminosity distance conversion
from astropy.cosmology import Planck18

# for generating mass distribution
from gwcosmo import priors as p

# for multiprocessing
# Import helper routines
from ..utils import rejection_sample, rejection_sample2d, update_dict


class SourceGalaxyPopulationModel:
    """Class to generate a population of source galaxies.
    This class is inherited by :class:`~ler.ler.CompactBinaryPopulation` class.

    Parameters
    ----------
    z_min : `float`
        Minimum redshift of the source population
        default: 0.
    z_max : `float`
        Maximum redshift of the source population
        default: 10.
    event_type : `str`
        Type of event to generate.
        e.g. 'BBH', 'BNS', 'NSBH'
    merger_rate_density : `str`
        Type of merger rate density function to use
        default: None/'merger_rate_density_popI_II_oguri2018'
        for others see instance method in :class:`~ler.ler.SourceGalaxyPopulationModel`
    merger_rate_density_param : `dict`
        Dictionary of merger rate density function parameters
        default: dict(R0=23.9 * 1e-9, b2=1.6, b3=2.0, b4=30)
    cosmology : `astropy.cosmology`
        Cosmology to use
        default: Planck18

    Examples
    ----------
    >>> from ler.gw_source_population import SourceGalaxyPopulationModel
    >>> cbc = SourceGalaxyPopulationModel(z_min=0.0001, z_max=10, merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018")
    >>> zs = cbc.sample_source_redshifts(size=1000)
    >>> zs[:5]
    array([2.9613628 , 1.18360022, 2.47637065, 2.51401502, 4.22868975])

    Instance Attributes
    ----------
    SourceGalaxyPopulationModel has the following instance attributes:\n
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
    |:attr:`~merger_rate_density`         | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~merger_rate_density_param`   | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~normalization_pdf_z`         | `float`                          |
    +-------------------------------------+----------------------------------+
    |:attr:`~z_to_luminosity_distance`    | `scipy.interpolate.interpolate`  |
    +-------------------------------------+----------------------------------+
    |:attr:`~differential_comoving_volume`| `scipy.interpolate.interpolate`  |
    +-------------------------------------+----------------------------------+

    Instance Methods
    ----------
    SourceGalaxyPopulationModel has the following instance methods:\n
    +-------------------------------------+----------------------------------+
    | Methods                             | Type                             |
    +=====================================+==================================+
    | :meth:`~merger_rate_density_model_list`                                |
    +-------------------------------------+----------------------------------+
    |                                     | Function to list available       |
    |                                     | merger rate density functions    |
    |                                     | and its parameters               |
    +-------------------------------------+----------------------------------+
    |:meth:`~merger_rate_density_src_frame`                                  |
    +-------------------------------------+----------------------------------+
    |                                     | Function to compute the merger   |
    |                                     | rate density (source frame)      |
    +-------------------------------------+----------------------------------+
    |:meth:`~create_lookup_table`         | Function to create a lookup      |
    |                                     | table for the differential       |
    |                                     | comoving volume and luminosity   |
    |                                     | distance wrt redshift            |
    +-------------------------------------+----------------------------------+
    |:meth:`~sample_source_redshifts`     | Function to sample source        |
    |                                     | redshifts from the source        |
    |                                     | galaxy population model          |
    +-------------------------------------+----------------------------------+
    |:meth:`~merger_rate_density_bbh_popI_II_oguri2018`                      |
    +-------------------------------------+----------------------------------+
    |                                     | Function to compute the merger   |
    |                                     | rate density (PopI/PopII)        |
    |                                     | from Oguri et al. (2018)         |
    +-------------------------------------+----------------------------------+
    |:meth:`~star_formation_rate_madau_dickinson2014`                        |
    +-------------------------------------+----------------------------------+
    |                                     | Function to compute star         |
    |                                     | formation rate as given in       |
    |                                     | Eqn. 15 Madau & Dickinson (2014) |
    +-------------------------------------+----------------------------------+
    |:meth:`~merger_rate_density_bbh_popIII_ken2022`                         |
    +-------------------------------------+----------------------------------+
    |                                     | Function to compute the merger   |
    |                                     | rate density (PopIII)            |
    +-------------------------------------+----------------------------------+
    |:meth:`~merger_rate_density_primordial_ken2022`                         |
    +-------------------------------------+----------------------------------+
    |                                     | Function to compute the merger   |
    |                                     | rate density (Primordial)        |
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
    Cosmology to use for the redshift distribution. \n
    e.g. Planck18, WMAP9, FlatLambdaCDM(H0=70, Om0=0.3) etc.
    """

    def __init__(
        self,
        z_min=0.0,
        z_max=10.0,
        event_type="BBH",
        merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018",
        merger_rate_density_param=dict(R0=23.9 * 1e-9, b2=1.6, b3=2.0, b4=30),
        cosmology=None,
    ):
        # set attributes
        self.z_min = z_min
        self.z_max = z_max
        self.event_type = event_type
        self.cosmo = cosmology if cosmology else Planck18
        self.create_lookup_table(z_min, z_max)

        # Define the merger-rate density function/method instances
        try:
            self.merger_rate_density = getattr(self, merger_rate_density)
            self.merger_rate_density_param = merger_rate_density_param
        except:
            raise ValueError(
                f"merger_rate_density must be one of {self.merger_rate_density_model_list()}"
            )

        # To find the normalization constant of the pdf p(z)
        # Normalize the pdf
        self.normalization_pdf_z = quad(
            self.merger_rate_density_src_frame,
            z_min,
            z_max,
            args=(merger_rate_density_param,),
        )[0]

        return None

    def merger_rate_density_model_list(self):
        """
        Function to list available merger rate density functions and its parameters.

        Returns
        ----------
        model_list : `list`
            List of available merger rate density functions.
        """

        return dict(
            merger_rate_density_bbh_popI_II_oguri2018=dict(
                R0=23.9 * 1e-9, b2=1.6, b3=2.0, b4=30
            ),
            star_formation_rate_madau_dickinson2014=dict(af=2.7, bf=5.6, cf=2.9),
            merger_rate_density_bbh_popIII_ken2022=dict(
                n0=19.2 * 1e-9, aIII=0.66, bIII=0.3, zIII=11.6
            ),
            merger_rate_density_primordial_ken2022=dict(
                n0=0.044 * 1e-9, t0=13.786885302009708
            ),
        )

    def merger_rate_density_src_frame(self, zs, param=None):
        """
        Function to compute the merger rate density (source frame). The output is in source frame and is unnormalized.

        Parameters
        ----------
        zs : `float`
            Source redshifts
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. if the merger_rate_density is merger_rate_density_bbh_popI_II_oguri2018
            param = dict(R0=23.9*1e-9, b2=1.6, b3=2.0, b4=30)

        Returns
        ----------
        rate_density : `float`
            merger rate density
        """

        # Define the merger-rate density function
        rate_density = (
            self.merger_rate_density(zs, param=param)
            / (1 + zs)
            * self.differential_comoving_volume(zs)
        )

        return rate_density

    def create_lookup_table(self, z_min, z_max):
        """
        Function to create a lookup table for the differential comoving volume
        and luminosity distance wrt redshift.

        Parameters
        ----------
        z_min : `float`
            Minimum redshift of the source population
        z_max : `float`
            Maximum redshift of the source population

        Attributes
        ----------
        z_to_luminosity_distance : `scipy.interpolate.interpolate`
            Function to convert redshift to luminosity distance
        differential_comoving_volume : `scipy.interpolate.interpolate`
            Function to calculate the differential comoving volume
        """

        # initialing cosmological functions for fast calculation through interpolation
        z = np.linspace(z_min, z_max, 500)  # redshift
        luminosity_distance = self.cosmo.luminosity_distance(
            z
        ).value  # luminosity distance in Mpc
        self.z_to_luminosity_distance = interp1d(z, luminosity_distance, kind="cubic")

        # Create a lookup table for the differential comoving volume
        dVcdz = self.cosmo.differential_comoving_volume(z).value * 4 * np.pi
        self.differential_comoving_volume = interp1d(
            z, dVcdz, kind="linear", fill_value="extrapolate"
        )

        return None

    def sample_source_redshifts(self, size=1000, z_min=0.0, z_max=10.0, param=None):
        """
        Function to sample source redshifts (source frame) from the source galaxy population
        model

        Parameters
        ----------
        size : `int`
            Number of samples to draw
            default: 1000
        z_min : `float`
            Minimum redshift of the source population
            default: 0.
        z_max : `float`
            Maximum redshift of the source population
            default: 10.
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(z_min=0.0, z_max=10.0)
            default: None

        Returns
        ----------
        zs : `array`
            Array of sampled redshifts

        Examples
        ----------
        >>> from ler.gw_source_population import SourceGalaxyPopulationModel
        >>> cbc = SourceGalaxyPopulationModel(z_min=0.0001, z_max=10, merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018")
        >>> zs = cbc.sample_source_redshifts(size=1000)
        >>> zs[:5]
        array([2.9613628 , 1.18360022, 2.47637065, 2.51401502, 4.22868975])
        """

        # replace values with param, if given
        if param:
            z_min = param["z_min"]
            z_max = param["z_max"]

        # Define the merger-rate density function
        # Define the pdf p(z)
        # pdf_unnormalized = (
        #     lambda z: self.merger_rate_density(z, param=self.merger_rate_density_param)
        #     / (1 + z)
        #     * self.differential_comoving_volume(z)
        # )
        # Normalize the pdf
        pdf = (
            lambda z: self.merger_rate_density_src_frame(
                z, param=self.merger_rate_density_param
            )
            / self.normalization_pdf_z
        )
        # Sample the redshifts using rejection sampling
        zs = rejection_sample(pdf, z_min, z_max, size=size)

        return zs

    def merger_rate_density_bbh_popI_II_oguri2018(
        self, zs, R0=23.9 * 1e-9, b2=1.6, b3=2.0, b4=30, param=None
    ):
        """
        Function to compute the merger rate density (PopI/PopII). Reference: Oguri et al. (2018). The output is in detector frame and is unnormalized.

        Parameters
        ----------
        zs : `float`
            Source redshifts
        R0 : `float`
            local merger rate density at low redshift
            default: 23.9*1e-9 Mpc^-3 yr^-1
        b2 : `float`
            Fitting paramters
            default: 1.6
        b3 : `float`
            Fitting paramters
            default: 2.0
        b4 : `float`
            Fitting paramters
            default: 30
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(R0=23.9*1e-9, b2=1.6, b3=2.0, b4=30)
            default: None

        Returns
        ----------
        rate_density : `float`
            merger rate density

        Examples
        ----------
        >>> from ler.gw_source_population import SourceGalaxyPopulationModel
        >>> cbc = SourceGalaxyPopulationModel(z_min=0.0001, z_max=10, merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018")
        >>> rate_density = cbc.merger_rate_density(zs=0.0001) # local merger rate density at low redshift
        >>> rate_density  # Mpc^-3 yr^-1
        2.3903670073287287e-08
        """

        if self.event_type == "BNS":
            R0 = 170.0 * 1e-9
        if self.event_type == "NSBH":
            R0 = 27.0 * 1e-9

        if param:
            R0 = param["R0"]
            b2 = param["b2"]
            b3 = param["b3"]
            b4 = param["b4"]

        # rate_density = R0 * (b4 + 1) * np.exp(b2 * zs) / (b4 + np.exp(b3 * zs))
        rate_density = R0 * (b4 + 1) * np.exp(b2 * zs) / (b4 + np.exp(b3 * zs))

        return rate_density

    def star_formation_rate_madau_dickinson2014(
        self, zs, af=2.7, bf=5.6, cf=2.9, param=None
    ):
        """
        Function to compute star formation rate as given in Eqn. 15 Madau & Dickinson (2014).

        Parameters
        ----------
        zs : `float`
            Source redshifts
        af : `float`
            Fitting paramters
            default: 2.7
        bf : `float`
            Fitting paramters
            default: 5.6
        cf : `float`
            Fitting paramters
            default: 2.9
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(af=2.7, bf=5.6, cf=2.9)
            default: None

        Returns
        ----------
        rate_density : `float`
            merger rate density

        Examples
        ----------
        >>> from ler.gw_source_population import SourceGalaxyPopulationModel
        >>> cbc = SourceGalaxyPopulationModel(z_min=0.0001, z_max=10, merger_rate_density="star_formation_rate_madau_dickinson2014")
        >>> rate_density = cbc.merger_rate_density(zs=0.0001) # local merger rate density at low redshift
        >>> rate_density  # Mpc^-3 yr^-1
        0.014965510855362926
        """
        if param:
            af = param["af"]
            bf = param["bf"]
            cf = param["cf"]

        # rate density
        rate_density = 0.015 * (1 + zs) ** af / (1 + ((1 + zs) / cf) ** bf)

        return rate_density

    def merger_rate_density_popIII_ken2022(
        self, zs, n0=19.2 * 1e-9, aIII=0.66, bIII=0.3, zIII=11.6, param=None
    ):
        """
        Function to compute the unnormalized merger rate density (PopIII). Reference: Ng et al. 2022. The output is in detector frame and is unnormalized.

        Parameters
        ----------
        zs : `float`
            Source redshifts
        n0 : `float`
            normalization constant
            default: 19.2*1e-9
        aIII : `float`
            Fitting paramters
            default: 0.66
        bIII : `float`
            Fitting paramters
            default: 0.3
        zIII : `float`
            Fitting paramters
            default: 11.6
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(aIII=0.66, bIII=0.3, zIII=11.6)
            default: None

        Returns
        ----------
        rate_density : `float`
            merger rate density

        Examples
        ----------
        >>> from ler.gw_source_population import SourceGalaxyPopulationModel
        >>> pop = SourceGalaxyPopulationModel(z_min=5, z_max=40, event_type = "BBH", merger_rate_density="merger_rate_density_popIII_ken2022")
        >>> rate_density = pop.merger_rate_density(zs=10)
        >>> rate_density  # Mpc^-3 yr^-1
        1.5107979464621443e-08
        """

        if param:
            aIII = param["aIII"]
            bIII = param["bIII"]
            zIII = param["zIII"]

        # rate density
        rate_density = (
            n0
            * np.exp(aIII * (zs - zIII))
            / (bIII + aIII * np.exp((aIII + bIII) * (zs - zIII)))
        )

        return rate_density

    def merger_rate_density_primordial_ken2022(
        self, zs, n0=0.044 * 1e-9, t0=13.786885302009708, param=None
    ):
        """
        Function to compute the merger rate density (Primordial). Reference: Ng et al. 2022. The output is in detector frame and is unnormalized.

        Parameters
        ----------
        zs : `float`
            Source redshifts
        n0 : `float`
            normalization constant
            default: 0.044*1e-9
        t0 : `float`
            Present age of the Universe in Gyr
            default: 13.786885302009708
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(t0=13.786885302009708)

        Returns
        ----------
        rate_density : `float`
            merger rate density

        Examples
        ----------
        >>> from ler.gw_source_population import SourceGalaxyPopulationModel
        >>> pop = SourceGalaxyPopulationModel(z_min=5, z_max=40, event_type = "BBH", merger_rate_density="merger_rate_density_primordial_ken2022")
        >>> rate_density = pop.merger_rate_density(zs=10)
        >>> rate_density  # Mpc^-3 yr^-1
        9.78691173794454e-10
        """
        if param:
            t0 = param["t0"]

        # rate density
        rate_density = n0 * (self.cosmo.age(z=zs).value / t0) ** (-34 / 37)

        return rate_density


class CompactBinaryPopulation(SourceGalaxyPopulationModel):
    """Class to generate a population of compact binaries. It helps sample all the intrinsic and extrinsic parameters of compact binaries. This daughter class inherits from :class:`~ler.ler.SourceGalaxyPopulationModel` class.

    Parameters
    ----------
    z_min : `float`
        Minimum redshift of the source population
        default: 0.0001
    z_max : `float`
        Maximum redshift of the source population
        default: 10.
    event_type : `str`
        Type of event to generate.
        e.g. 'BBH', 'BNS', 'NSBH'
    event_priors, event_priors_params : `dict`, `dict`
        Dictionary of prior sampler functions and its input parameters.
        Check for available priors and corresponding inout parameters by running,
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> cbc.available_prior_list_and_its_params()
    spin_zero : `bool`
        If True, spin prior is set to zero.
        default: True
    cosmology : `astropy.cosmology`
        Cosmology to use
        default: Planck18

    Examples
    ----------
    >>> from ler.gw_source_population import CompactBinaryPopulation
    >>> cbc = CompactBinaryPopulation()
    >>> params = cbc.sample_gw_parameters(size=1000)
    >>> params.keys()
    dict_keys(['zs', 'geocent_time', 'sky_position', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2'])

    Instance Attributes
    ----------
    CompactBinaryPopulation has the following instance attributes:\n
    +-------------------------------------+----------------------------------+
    | Atrributes                          | Type                             |
    +=====================================+==================================+
    |:attr:`~z_min`                       | `float`                          |
    +-------------------------------------+----------------------------------+
    |:attr:`~z_max`                       | `float`                          |
    +-------------------------------------+----------------------------------+
    |:attr:`~event_type`                  | `str`                            |
    +-------------------------------------+----------------------------------+
    |:attr:`~event_priors`                | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~event_priors_params`         | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~spin_zero`                   | `bool`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_samplers`           | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~gw_param_samplers_params`    | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~sampler_names`               | `dict`                           |
    +-------------------------------------+----------------------------------+
    |:attr:`~prior_bilby`                 | `bilby.gw.prior.BBHPriorDict`    |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_source_frame_masses`  | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_geocent_time`         | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_source_redshifts`     | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_sky_position`         | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_coalescence_phase`    | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_polarization_angle`   | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_inclination`          | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_luminosity_distance`  | `function`                       |
    +-------------------------------------+----------------------------------+
    |:attr:`~sample_spin`                 | `function`                       |
    +-------------------------------------+----------------------------------+

    Instance Methods
    ----------
    CompactBinaryPopulation has the following instance methods:\n
    +-------------------------------------+----------------------------------+
    | Methods                             | Type                             |
    +=====================================+==================================+
    |:meth:`~event_priors_categorization`                                    |
    +-------------------------------------+----------------------------------+
    |                                     | Function to categorize the event |
    |                                     | priors and its parameters        |
    +-------------------------------------+----------------------------------+
    |:meth:`~sample_gw_parameters`        | Function to sample all the       |
    |                                     | intrinsic and extrinsic          |
    |                                     | parameters of compact binaries   |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_masses_BBH_popI_II_powerlaw_gaussian`                    |
    +-------------------------------------+----------------------------------+
    |                                     | Function to sample source mass1  |
    |                                     | and mass2 with PowerLaw+PEAK     |
    |                                     | model                            |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_masses_BBH_popIII_lognormal`                             |
    +-------------------------------------+----------------------------------+
    |                                     | Function to sample source mass1  |
    |                                     | and mass2 with popIII orgin from |
    |                                     | lognormal distribution. Refer to |
    |                                     | Ng et al. 2022. Eqn. 1 and 4     |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_masses_BBH_primordial_lognormal`                         |
    +-------------------------------------+----------------------------------+
    |                                     | Function to sample source mass1  |
    |                                     | and mass2 with primordial orgin  |
    |                                     | from lognormal distribution.     |
    |                                     | Refer to Ng et al. 2022. Eqn. 1  |
    |                                     | and 4                            |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_masses_BNS_popI_II_gwcosmo`                              |
    +-------------------------------------+----------------------------------+
    |                                     | Function to sample source mass1  |
    |                                     | and mass2 from powerlaw          |
    |                                     | distribution.                    |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_masses_BNS_bimodal`   | Function to sample source mass1  |
    |                                     | and mass2 from bimodal           |
    |                                     | distribution. Refer to           |
    |                                     | Will M. Farr et al. 2020 Eqn. 6  |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_spin_BBH_bilby`       | Function to sample BBH source    |
    |                                     | spin from bilby prior            |
    +-------------------------------------+----------------------------------+
    |:meth:`~binary_spin_aligned`         | Function to sample BBH source    |
    |                                     | spin for aligned and antialigned |
    |                                     | case.                            |
    +-------------------------------------+----------------------------------+
    |:meth:`~constant_values_n_size`      | Function to return array of      |
    |                                     | constant values of size n        |
    +-------------------------------------+----------------------------------+
    |:meth:`~geocent_time_uniform`        | Function to sample geocent time  |
    |                                     | from uniform distribution        |
    +-------------------------------------+----------------------------------+
    |:meth:`~sky_position_uniform_bilby ` | Function to sample sky position  |
    |                                     | from bilby prior                 |
    +-------------------------------------+----------------------------------+
    |:meth:`~coalescence_phase_uniform`   | Function to sample coalescence   |
    |                                     | phase from uniform distribution  |
    |                                     | in radians (using bilby prior)   |
    +-------------------------------------+----------------------------------+
    |:meth:`~polarization_angle_uniform`  | Function to sample polarization  |
    |                                     | angle from uniform distribution  |
    |                                     | in radians (using bilby prior)   |
    +-------------------------------------+----------------------------------+
    |:meth:`~inclination_uniform`         | Function to sample inclination   |
    |                                     | from uniform distribution        |
    |                                     | in radians (using bilby prior)   |
    +-------------------------------------+----------------------------------+
    |:meth:`~available_prior_list_and_its_params                             |
    +-------------------------------------+----------------------------------+
    |                                     | Function to list available       |
    |                                     | sampler function and its         |
    |                                     | parameters                       |
    +-------------------------------------+----------------------------------+

    Examples
    ----------
    >>> from ler.gw_source_population import CompactBinaryPopulation
    >>> cbc = CompactBinaryPopulation()
    >>> params = cbc.sample_gw_parameters(size=1000)
    >>> params.keys()
    dict_keys(['zs', 'geocent_time', 'sky_position', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2'])
    >>> params["zs"][:5]
    array([3.7372458 , 1.27830786, 4.43500934, 2.83264988, 2.73744203])
    """

    def __init__(
        self,
        z_min=0.0,
        z_max=10.0,
        event_type="BBH",
        event_priors=None,
        event_priors_params=None,
        spin_zero=True,
        cosmology=None,
    ):
        # set attributes
        self.z_min = z_min
        self.z_max = z_max
        self.spin_zero = spin_zero

        # dealing with prior functions and categorization
        (
            self.gw_param_samplers,
            self.gw_param_samplers_params,
            self.sampler_names,
        ) = self.event_priors_categorization(
            event_type, event_priors, event_priors_params
        )

        # initialize the SourceGalaxyPopulationModel mother class
        # for redshift distribution
        # instance attribute sample_source_redshifts is initialized here
        super().__init__(
            z_min=z_min,
            z_max=z_max,
            event_type=event_type,
            merger_rate_density=self.gw_param_samplers["merger_rate_density"],
            merger_rate_density_param=self.gw_param_samplers_params[
                "merger_rate_density"
            ],
            cosmology=cosmology,
        )

        # initialize the spin prior attribute
        # remove spin prior if spin_zero is True
        if spin_zero:
            del self.gw_param_samplers["spin"]
            del self.gw_param_samplers_params["spin"]
            del self.sampler_names["sample_spin"]
        else:
            self.sample_spin = getattr(self, self.gw_param_samplers["spin"])

        # initializing bilby prior
        bilby.core.utils.logger.disabled = True
        self.prior_bilby = bilby.gw.prior.BBHPriorDict()

        # defining samplers
        # try: gets instance method; except: if custom sampler is prvided
        try:
            self.sample_source_frame_masses = getattr(
                self, self.gw_param_samplers["source_frame_masses"]
            )
        except:
            self.sample_source_frame_masses = self.gw_param_samplers[
                "source_frame_masses"
            ]
        try:
            self.sample_geocent_time = getattr(
                self, self.gw_param_samplers["geocent_time"]
            )
        except:
            self.sample_geocent_time = self.gw_param_samplers["geocent_time"]
        try:
            self.sample_source_redshifts = getattr(self, self.gw_param_samplers["zs"])
        except:
            self.sample_source_redshifts = self.gw_param_samplers["zs"]
        try:
            self.sample_sky_position = getattr(
                self, self.gw_param_samplers["sky_position"]
            )
        except:
            self.sample_sky_position = self.gw_param_samplers["sky_position"]
        try:
            self.sample_coalescence_phase = getattr(
                self, self.gw_param_samplers["phase"]
            )
        except:
            self.sample_coalescence_phase = self.gw_param_samplers["phase"]
        try:
            self.sample_polarization_angle = getattr(
                self, self.gw_param_samplers["psi"]
            )
        except:
            self.sample_polarization_angle = self.gw_param_samplers["psi"]
        try:
            self.sample_inclination = getattr(self, self.gw_param_samplers["theta_jn"])
        except:
            self.sample_inclination = self.gw_param_samplers["theta_jn"]

        return None

    def event_priors_categorization(self, event_type, event_priors, event_prior_params):
        """
        Function to categorize the event priors and its parameters.

        Parameters
        ----------
        event_type : `str`
            Type of event to generate.
            e.g. 'BBH', 'BNS', 'BBH_popIII', 'BBH_primordial', 'NSBH'
        event_priors : `dict`
            Dictionary of prior sampler functions for each parameter
        event_prior_params : `dict`
            Dictionary of sampler parameters for each parameter

        Returns
        ----------
        event_priors_ : `dict`
            Dictionary of prior sampler functions for each parameter
        event_prior_params_ : `dict`
            Dictionary of sampler parameters for each parameter

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> print("default priors=",cbc.gw_param_samplers)
        >>> print("default priors's parameters=",cbc.gw_param_samplers_params)
        """
        # for BBH
        if event_type == "BBH":
            event_priors_ = dict(
                merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018",
                source_frame_masses="binary_masses_BBH_popI_II_powerlaw_gaussian",
                spin="binary_spin_BBH_bilby",
                zs="sample_source_redshifts",
                geocent_time="geocent_time_uniform",
                sky_position="sky_position_uniform_bilby",
                phase="coalescence_phase_uniform_bilby",
                psi="polarization_angle_uniform_bilby",
                theta_jn="inclination_uniform_bilby",
            )
            event_prior_params_ = dict(
                merger_rate_density=dict(R0=23.9 * 1e-9, b2=1.6, b3=2.0, b4=30),
                source_frame_masses=dict(
                    mminbh=4.98,
                    mmaxbh=86.22,
                    alpha=2.63,
                    mu_g=33.07,
                    sigma_g=5.69,
                    lambda_peak=0.10,
                    delta_m=4.82,
                    beta=1.26,
                ),
                spin=None,
                zs=dict(z_min=self.z_min, z_max=self.z_max),
                geocent_time=dict(
                    start_time=1238166018, end_time=1238166018 + 31536000
                ),
                sky_position=None,
                phase=None,
                psi=None,
                theta_jn=None,
            )
        # for BNS
        if event_type == "BNS":
            event_priors_ = dict(
                merger_rate_density="merger_rate_density_bbh_popI_II_oguri2018",
                source_frame_masses="binary_masses_BNS_bimodal",
                spin="binary_spin_aligned",
                zs="sample_source_redshifts",
                geocent_time="geocent_time_uniform",
                sky_position="sky_position_uniform_bilby",
                phase="coalescence_phase_uniform_bilby",
                psi="polarization_angle_uniform_bilby",
                theta_jn="inclination_uniform_bilby",
            )
            event_prior_params_ = dict(
                merger_rate_density=dict(R0=170.0 * 1e-9, b2=1.6, b3=2.0, b4=30),
                source_frame_masses=dict(
                    w=0.643,
                    muL=1.352,
                    sigmaL=0.08,
                    muR=1.88,
                    sigmaR=0.3,
                    mmin=1.0,
                    mmax=2.3,
                ),
                spin=dict(a_min=-0.05, a_max=0.05),
                zs=dict(z_min=self.z_min, z_max=self.z_max),
                geocent_time=dict(
                    start_time=1238166018, end_time=1238166018 + 31536000
                ),
                sky_position=None,
                phase=None,
                psi=None,
                theta_jn=None,
            )
        if event_type == "NSBH":
            pass

        # update the priors if input is given
        if event_priors:
            event_priors_ = update_dict(event_priors_, event_priors)
        if event_prior_params:
            event_prior_params_ = update_dict(event_prior_params_, event_prior_params)

        # dict of sampler names with description
        sampler_names_ = dict(
            sample_source_frame_masses="samples mass1 and mass2 of the compact binaries",
            sample_spin="samples spin parameters of the compact binaries",
            sample_source_redshifts="samples source redshifts",
            sample_geocent_time="samples geocent_time",
            sample_sky_position="samples sky position",
            sample_coalescence_phase="samples coalescence phase",
            sample_polarization_angle="samples polarization angle",
            sample_inclination="samples inclination",
        )

        return (event_priors_, event_prior_params_, sampler_names_)

    def sample_gw_parameters(self, size=1000, **kwargs):
        """
        Function to sample BBH/BNS/NSBH intrinsic and extrinsics parameters

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        kwargs : `dict`
            Keyword arguments to pass in parameter values
            e.g. zs = np.array([0.1,0.2,0.3])

        Returns
        ----------
        gw_parameters : `dict`
            Dictionary of sampled parameters
            gw_parameters.keys() = ['mass_1', 'mass_2', 'mass_1_source', 'mass_2_source', 'zs', 'luminosity_distance', 'inclination', 'polarization_angle', 'phase', 'geocent_time', 'ra', 'dec', 'a_1', 'a_2', 'tilt_1', 'tilt_2', 'phi_12', 'phi_jl']

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> params = cbc.sample_gw_parameters(size=1000)
        >>> params.keys()
        dict_keys(['zs', 'geocent_time', 'sky_position', 'phase', 'psi', 'theta_jn', 'luminosity_distance', 'mass_1_source', 'mass_2_source', 'mass_1', 'mass_2'])
        """

        # sample parameters
        param_names = list(self.gw_param_samplers.keys())
        samplers_params = list(self.gw_param_samplers_params.values())
        del param_names[0]  # remove merger_rate_density
        del samplers_params[0]  # remove merger_rate_density
        # make sure the order is correct
        sampler_names = list(self.sampler_names.keys())

        gw_parameters = {}  # initialize dictionary to store parameters
        for name, sampler, param in zip(param_names, sampler_names, samplers_params):
            if name not in kwargs:
                # Sample the parameter using the specified sampler function
                gw_parameters[name] = getattr(self, sampler)(size=size, param=param)
            else:
                # Use the provided value from kwargs
                gw_parameters[name] = kwargs[name]

        # calculate luminosity distance
        zs = gw_parameters["zs"]
        gw_parameters["luminosity_distance"] = self.z_to_luminosity_distance(zs)  # Mpc
        # mass1 and mass2
        gw_parameters["mass_1_source"], gw_parameters["mass_2_source"] = gw_parameters[
            "source_frame_masses"
        ]  # Msun
        gw_parameters["mass_1"], gw_parameters["mass_2"] = gw_parameters[
            "mass_1_source"
        ] * (1 + zs), gw_parameters["mass_2_source"] * (
            1 + zs
        )  # Msun
        del gw_parameters["source_frame_masses"]
        # spin
        if not self.spin_zero:
            (
                gw_parameters["a_1"],
                gw_parameters["a_2"],
                gw_parameters["tilt_1"],
                gw_parameters["tilt_2"],
                gw_parameters["phi_12"],
                gw_parameters["phi_jl"],
            ) = gw_parameters["spin"]
            del gw_parameters["spin"]

        return gw_parameters

    def binary_masses_BBH_popI_II_powerlaw_gaussian(
        self,
        size,
        mminbh=4.98,
        mmaxbh=86.22,
        alpha=2.63,
        mu_g=33.07,
        sigma_g=5.69,
        lambda_peak=0.10,
        delta_m=4.82,
        beta=1.26,
        param=None,
    ):
        """
        Function to sample source mass1 and mass2 with PowerLaw+PEAK model

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        mminbh : `float`
            Minimum mass of the black hole
            default: 4.98
        mmaxbh : `float`
            Maximum mass of the black hole
            default: 86.22
        alpha : `float`
            Spectral index for the powerlaw of the primary mass distribution
            default: 2.63
        mu_g : `float`
            Mean of the Gaussian component in the primary mass distribution
            default: 33.07
        sigma_g : `float`
            Width of the Gaussian component in the primary mass distribution
            default: 5.69
        lambda_peak : `float`
            Fraction of the model in the Gaussian component
            default: 0.10
        delta_m : `float`
            Range of mass tapering on the lower end of the mass distribution
            default: 4.82
        beta : `float`
            Spectral index for the powerlaw of the mass ratio distribution
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(mminbh=4.98, mmaxbh=86.22, alpha=2.63, mu_g=33.07, sigma_g=5.69, lambda_peak=0.10, delta_m=4.82, beta=1.26)
        Returns
        ----------
        mass_1_source : `array`
            Array of mass1 in source frame
        mass_2_source : `array`
            Array of mass2 in source frame

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> m1_src, m2_src = cbc.binary_masses_BBH_popI_II_powerlaw_gaussian(size=1000)
        """

        if param:
            mminbh = param["mminbh"]
            mmaxbh = param["mmaxbh"]
            alpha = param["alpha"]
            mu_g = param["mu_g"]
            sigma_g = param["sigma_g"]
            lambda_peak = param["lambda_peak"]
            delta_m = param["delta_m"]
            beta = param["beta"]

        # mass function
        model = p.BBH_powerlaw_gaussian(
            mminbh=mminbh,
            mmaxbh=mmaxbh,
            alpha=alpha,
            mu_g=mu_g,
            sigma_g=sigma_g,
            lambda_peak=lambda_peak,
            delta_m=delta_m,
            beta=beta,
        )
        # sample mass1 and mass2
        mass_1_source, mass_2_source = model.sample(Nsample=size)

        return (mass_1_source, mass_2_source)

    def binary_masses_BBH_popIII_lognormal(
        self, size, m_min=5.0, m_max=150.0, Mc=30.0, sigma=0.3, param=None
    ):
        """
        Function to sample source mass1 and mass2 with pop III origin. Refer to Eqn. 1 and 4 of Ng et al. 2022

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        m_min : `float`
            Minimum mass of the black hole (popIII)
            default: 10.
        m_max : `float`
            Maximum mass of the black hole (popIII)
            default: 100.
        Mc    : `float`
            Mass scale; the distribution is centered around Mc
            default: 30.0
        sigma : `float`
            Width of the distribution
            default: 0.3
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(m_min=10., m_max=100., Mc=30.0, sigma=0.3)

        Returns
        ----------
        mass_1_source : `array`
            Array of mass1 in source frame
        mass_2_source : `array`
            Array of mass2 in source frame

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> m1_src, m2_src = cbc.binary_masses_BBH_popIII_lognormal(size=1000)
        """

        if param:
            m_min = param["m_min"]
            m_max = param["m_max"]
            Mc = param["Mc"]
            sigma = param["sigma"]

        # mass function for popIII
        psi = lambda m: np.exp(-np.log(m / Mc) ** 2 / (2 * sigma**2)) / (
            np.sqrt(2 * np.pi) * sigma * m
        )
        # probability density function
        pdf = (
            lambda m1, m2: (m1 + m2) ** (36 / 37)
            * (m1 * m2) ** (32 / 37)
            * psi(m1)
            * psi(m2)
        )
        # rejection sampling
        mass_1_source, mass_2_source = rejection_sample2d(
            pdf=pdf, xmin=m_min, xmax=m_max, ymin=m_min, ymax=m_max, size=size
        )
        # swap the masses if mass_2_source > mass_1_source
        idx = mass_2_source > mass_1_source
        mass_1_source[idx], mass_2_source[idx] = mass_2_source[idx], mass_1_source[idx]

        return (mass_1_source, mass_2_source)

    def binary_masses_BBH_primordial_lognormal(
        self, size, m_min=1.0, m_max=100.0, Mc=20.0, sigma=0.3, param=None
    ):
        """
        Function to sample source mass1 and mass2 with primordial origin. Refer to Eqn. 1 and 4 of Ng et al. 2022

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        m_min : `float`
            Minimum mass of the black hole (primordial)
            default: 10.
        m_max : `float`
            Maximum mass of the black hole (primordial)
            default: 100.
        Mc, sigma : `float`
            Fitting parameters
            default: Mc=30.0, sigma=0.3
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(m_min=10., m_max=100., Mc=30.0, sigma=0.3)

        Returns
        ----------
        mass_1_source : `array`
            Array of mass1 in source frame
        mass_2_source : `array`
            Array of mass2 in source frame
        """

        if param:
            m_min = param["m_min"]
            m_max = param["m_max"]
            Mc = param["Mc"]
            sigma = param["sigma"]

        # mass function for primordial
        psi = lambda m: np.exp(-np.log(m / Mc) ** 2 / (2 * sigma**2)) / (
            np.sqrt(2 * np.pi) * sigma * m
        )
        # probability density function
        pdf = (
            lambda m1, m2: (m1 + m2) ** (36 / 37)
            * (m1 * m2) ** (32 / 37)
            * psi(m1)
            * psi(m2)
        )
        # rejection sampling
        mass_1_source, mass_2_source = rejection_sample2d(
            pdf=pdf, xmin=m_min, xmax=m_max, ymin=m_min, ymax=m_max, size=size
        )
        # swap the masses if mass_2_source > mass_1_source
        idx = mass_2_source > mass_1_source
        mass_1_source[idx], mass_2_source[idx] = mass_2_source[idx], mass_1_source[idx]

        return (mass_1_source, mass_2_source)

    def binary_masses_BNS_popI_II_gwcosmo(
        self, size, mminns=1.0, mmaxns=3.0, alphans=0.0, param=None
    ):
        """
        Function to calculate source mass1 and mass2 of BNS from powerlaw distribution (gwcosmo)

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        mminns : `float`
            Minimum mass of the BNS
            default: 1.0
        mmaxns : `float`
            Maximum mass of the BNS
            default: 3.0
        alphans : `float`
            Power law index
            default: 0.0

        Returns
        ----------
        mass_1_source : `array`
            Array of mass1 in source frame
        mass_2_source : `array`
            Array of mass2 in source frame

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> m1_src, m2_src = cbc.binary_masses_BNS_popI_II_gwcosmo(size=1000)
        """

        if param:
            mminns = param["mminns"]
            mmaxns = param["mmaxns"]
            alphans = param["alphans"]

        # mass function for BNS
        model = p.BNS(mminns=mminns, mmaxns=mmaxns, alphans=alphans)
        # sampling
        mass_1_source, mass_2_source = model.sample(Nsample=size)

        return (mass_1_source, mass_2_source)

    def binary_masses_BNS_bimodal(
        self,
        size,
        w=0.643,
        muL=1.352,
        sigmaL=0.08,
        muR=1.88,
        sigmaR=0.3,
        mmin=1.0,
        mmax=2.3,
        param=None,
    ):
        """
        Function to calculate source mass1 and mass2 of BNS (Alsing). It is a double peak power-law model (with mass cut) of binary neutron stars' mass in the paper titled "A Population-Informed Mass Estimate for Pulsar J0740+6620".

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        w : `float`
            Weight of the left peak
            default: 0.643
        muL, sigmaL : `float`
            Mean and standard deviation of the left peak
            default: muL=1.352, sigmaL=0.08
        muR, sigmaR : `float`
            Mean and standard deviation of the right peak
            default: muR=1.88, sigmaR=0.3
        mmin : `float`
            Minimum mass of the BNS
            default: 1.0
        mmax : `float`
            Maximum mass of the BNS
            default: 2.3
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(w=0.643, muL=1.352, sigmaL=0.08, muR=1.88, sigmaR=0.3, mmin=1.0, mmax=2.3)

        Returns
        ----------
        mass_1_source : `array`
            Array of mass1 in source frame
        mass_2_source : `array`
            Array of mass2 in source frame

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> m1_src, m2_src = cbc.binary_masses_BNS_bimodal(size=1000)
        """

        if param:
            w, muL, sigmaL, muR, sigmaR, mmin, mmax = (
                param["w"],
                param["muL"],
                param["sigmaL"],
                param["muR"],
                param["sigmaR"],
                param["mmin"],
                param["mmax"],
            )

        # left and right peak
        pdf_unnormL = lambda m: np.exp(-((m - muL) ** 2) / (2 * sigmaL**2))
        normL = quad(pdf_unnormL, mmin, mmax)[0]  # normalization constant
        pdf_unnormR = lambda m: np.exp(-((m - muR) ** 2) / (2 * sigmaR**2))
        normR = quad(pdf_unnormR, mmin, mmax)[0]  # normalization constant
        # total pdf
        pdf = lambda m: w * pdf_unnormL(m) / normL + (1 - w) * pdf_unnormR(m) / normR

        mass_1_source = rejection_sample(pdf, mmin, mmax, size=size)
        mass_2_source = rejection_sample(pdf, mmin, mmax, size=size)
        # swap mass_1_source and mass_2_source if mass_2_source > mass_1_source
        idx = mass_2_source > mass_1_source
        mass_1_source[idx], mass_2_source[idx] = mass_2_source[idx], mass_1_source[idx]

        return (mass_1_source, mass_2_source)

    def mass_ratio_powerlaw(self, size, beta=1.1):
        """
        Function to calculate mass ratio with power law distribution.

        Parameters
        ----------
        size : `int`
            Number of samples
        beta : `float`
            Power law index

        Returns
        ----------
        q : `array`
            Array of mass ratio

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> ratio = cbc.mass_ratio_powerlaw(size=1000)
        """

        pdf = lambda q: q**beta
        q = rejection_sample(pdf, 0, 1, size=size)

        return q

    def binary_spin_BBH_bilby(self, size, param=None):
        """
        Function to calculate spin parameters of BBH with bilby prior.

        Parameters
        ----------
        size : `int`
            Number of samples to draw

        Returns
        ----------
        a_1 : `array`
            Array of spin1
        a_2 : `array`
            Array of spin2
        tilt_1 : `array`
            Array of tilt1
        tilt_2 : `array`
            Array of tilt2
        phi_12 : `array`
            Array of phi12
        phi_jl : `array`
            Array of phi_jl

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> a1, a2, tilt1, tilt2, phi12, phi_jl = cbc.binary_spin_BBH_bilby(size=1000)
        """
        bilby.core.utils.logger.disabled = True
        prior_default = bilby.gw.prior.BBHPriorDict()
        a_1 = prior_default["a_1"].sample(size)
        a_2 = prior_default["a_2"].sample(size)
        tilt_1 = prior_default["tilt_1"].sample(size)
        tilt_2 = prior_default["tilt_2"].sample(size)
        phi_12 = prior_default["phi_12"].sample(size)
        phi_jl = prior_default["phi_jl"].sample(size)

        return (a_1, a_2, tilt_1, tilt_2, phi_12, phi_jl)

    def binary_spin_aligned(self, size, a_min=-0.05, a_max=0.05, param=None):
        """
        Function to sample aligned/anti-aligned spin parameters a1 and a2. a1 and a2 constraint between a_min and a_max.

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        a_min : `float`
            Minimum value of spin
            default: -0.05
        a_max : `float`
            Maximum value of spin
            default: 0.05
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(a_min=-0.05, a_max=0.05)

        Returns
        ----------
        a_1 : `array`
            Array of spin1
        a_2 : `array`
            Array of spin2
        
        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> a1, a2 = cbc.binary_spin_aligned(size=1000)
        """

        if param:
            a_min = param["a_min"]
            a_max = param["a_max"]

        a_1 = np.random.uniform(a_min, a_max, size=size)  # spin1
        a_2 = np.random.uniform(a_min, a_max, size=size)  # spin2
        tilt_1, tilt_2, phi_12, phi_jl = (
            np.zeros(size),
            np.zeros(size),
            np.zeros(size),
            np.zeros(size),
        )

        return (a_1, a_2, tilt_1, tilt_2, phi_12, phi_jl)

    def constant_values_n_size(self, size=100, value=0.0, param=None):
        """
        Function to sample constant values

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        value : `float`
            Constant value
            default: 0.0
        param : `dict`
            Allows to pass in above parameters as dict.
            e.g. param = dict(value=0.0)

        Returns
        ----------
        value : `array`
            Array of constant values

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> value = cbc.constant_values_n_size(size=1000)
        """

        if param:
            value = param["value"]

        return np.ones(size) * value

    def geocent_time_uniform(
        self, size, start_time=1238166018, end_time=1238166018 + 31536000, param=None
    ):
        """
        Function to sample geocent_time from uniform distribution

        Parameters
        ----------
        size : `int`
            Number of samples to draw
        start_time : `float`
            Start time of the uniform distribution
            default: 1238166018
        end_time : `float`
            End time of the uniform distribution
            default: 1238166018 + 31536000

        Returns
        ----------
        geocent_time : `array`
            Array of geocent_time or time of coalescence

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> time = cbc.geocent_time_uniform(size=1000)
        """

        if param:
            start_time = param["start_time"]
            end_time = param["end_time"]

        geocent_time = np.random.uniform(start_time, end_time, size=size)

        return geocent_time

    def sky_position_uniform_bilby(self, size, param=None):
        """
        Function to sample sky position from bilby prior

        Parameters
        ----------
        size : `int`
            Number of samples to draw

        Returns
        ----------
        ra : `array`
            Array of right ascension
        dec : `array`
            Array of declination

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> ra, dec = cbc.sky_position_uniform_bilby(size=1000)
        """

        ra = self.prior_bilby["ra"].sample(size)
        dec = self.prior_bilby["dec"].sample(size)

        return (ra, dec)

    def coalescence_phase_uniform_bilby(self, size, param=None):
        """
        Function to sample coalescence_phase from bilby prior

        Parameters
        ----------
        size : `int`
            Number of samples to draw

        Returns
        ----------
        phase : `array`
            Array of phase of coalescence

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> phase = cbc.coalescence_phase_uniform_bilby(size=1000)
        """

        return self.prior_bilby["phase"].sample(size)

    def polarization_angle_uniform_bilby(self, size, param=None):
        """
        Function to sample polarization_angle from bilby prior

        Parameters
        ----------
        size : `int`
            Number of samples to draw

        Returns
        ----------
        polarization_angle : `array`
            Array of polarization angle

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> psi = cbc.polarization_angle_uniform_bilby(size=1000)
        """

        return self.prior_bilby["psi"].sample(size)

    def inclination_uniform_bilby(self, size, param=None):
        """
        Function to sample inclination from bilby prior

        Parameters
        ----------
        size : `int`
            Number of samples to draw

        Returns
        ----------
        inclination : `array`
            Array of inclination angle

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> cbc = CompactBinaryPopulation()
        >>> theta_jn = cbc.inclination_uniform_bilby(size=1000)
        """

        return self.prior_bilby["theta_jn"].sample(size)

    def available_prior_list_and_its_params(self):
        """
        Function to list all the available priors. Prior of zs is not included as is the redshift sampler from the SourceGalaxyPopulationModel.

        Returns
        ----------
        event_prior_list_and_its_params_ : `dict`
            Dictionary of prior sampler functions for each parameter
            and its parameters.

        Examples
        ----------
        >>> from ler.gw_source_population import CompactBinaryPopulation
        >>> pop = CompactBinaryPopulation()
        >>> priors = pop.available_prior_list_and_its_params()
        >>> priors.keys()  # type of priors
        dict_keys(['merger_rate_density', 'source_frame_masses', 'spin', 'geocent_time', 'sky_position', 'phase', 'polarization_angle', 'inclination'])
        >>> priors['source_frame_masses'].keys()  # type of source_frame_masses priors
        dict_keys(['binary_masses_BBH_popI_II_powerlaw_gaussian', 'binary_masses_BBH_popIII_lognormal', 'binary_masses_BBH_primordial_lognormal', 'binary_masses_BNS_popI_II_gwcosmo', 'binary_masses_BNS_bimodal'])
        >>> priors['source_frame_masses']['binary_masses_BBH_popI_II_powerlaw_gaussian'].keys()  # parameters of binary_masses_BBH_popI_II_powerlaw_gaussian
        dict_keys(['mminbh', 'mmaxbh', 'alpha', 'mu_g', 'sigma_g', 'lambda_peak', 'delta_m', 'beta'])
        """

        event_prior_list_and_its_params_ = dict(
            merger_rate_density=self.merger_rate_density_model_list(),
            source_frame_masses=dict(
                binary_masses_BBH_popI_II_powerlaw_gaussian=dict(
                    mminbh=4.98,
                    mmaxbh=112.5,
                    alpha=3.78,
                    mu_g=32.27,
                    sigma_g=3.88,
                    lambda_peak=0.03,
                    delta_m=4.8,
                    beta=0.81,
                ),
                binary_masses_BBH_popIII_lognormal=dict(Mc=30.0, sigma=0.3, beta=1.1),
                binary_masses_BBH_primordial_lognormal=dict(
                    Mc=30.0, sigma=0.3, beta=1.1
                ),
                binary_masses_BNS_popI_II_gwcosmo=dict(
                    mminns=1.0, mmaxns=3.0, alphans=0.0
                ),
                binary_masses_BNS_bimodal=dict(
                    w=0.643,
                    muL=1.352,
                    sigmaL=0.08,
                    muR=1.88,
                    sigmaR=0.3,
                    mmin=1.0,
                    mmax=2.3,
                ),
            ),
            zs=dict(
                sample_source_redshifts=dict(
                    zs=dict(z_min=self.z_min, z_max=self.z_max)
                ),
            ),
            spin=dict(
                constant_values_n_size=dict(value=0.0),
                binary_spin_BBH_bilby=None,
                binary_spin_BNS_bilby=None,
            ),
            geocent_time=dict(
                geocent_time_uniform=dict(
                    start_time=1238166018, end_time=1238166018 + 31536000
                )
            ),
            sky_position=dict(sky_position_uniform_bilby=None),
            phase=dict(coalescence_phase_uniform_bilby=None),
            psi=dict(polarization_angle_uniform_bilby=None),
            theta_jn=dict(inclination_uniform_bilby=None),
        )

        return event_prior_list_and_its_params_
