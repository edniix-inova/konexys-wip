import logging
import os
import sys
from pathlib import Path
from typing import Tuple, Optional, Union, List

from utilities.generic import check_create_directory, run_command
from utilities.generic import read_config
from konexys.setup.paths import PATH_SUMO_BIN, PATH_SUMO_TOOLS

KEY_ENCODING = 'UTF-8'
# keys for config file sumo_manager.yaml
KEY_NETCONVERT_BIN = 'netconvert'
KEY_POLYCONVERT_BIN = 'polyconvert'
KEY_SUMO_BIN = 'sumo'
KEY_NET_FILE = 'net_file'
KEY_POIS_FILE = 'pois_file'
KEY_VTYPE_TEMPLATE_FILE = 'vtype_template_file'
KEY_RANDOM_TRIPS_FILE = 'random_trips_file'
KEY_RANDOM_ROUTES_FILE = 'random_routes_file'
KEY_CSV_SUFFIX = '.csv'


class SumoManager:
    """Management class for SUMO (Simulation of Urban MObility).

    The interface to Sumo is through a terminal command by starting either a
    sumo binary or a sumo tool python script.

    Private Attributes
    ------------------
    _config : dict
    _scenario_dir : str
    _output_dir: str
    _postprocessing_dir: str

    Public Methods:
    ---------------
    get_<Private Attributes>()
    process_map(): only open-street-map implemented
    run_simulation(): defined in subclasses
    transform_data(): transforms the simulation output to csv, pickle files
    """

    def __init__(self,
                 config_path: Path,
                 output_dir: Path,
                 ):
        """ Set class parameters, read the config file and check and create 
        the directories.
        
        Parameters
        ----------
        config_path : Path
        output_dir: Path
        """

        logging.info(f'Sumo config file: {config_path}')
        logging.info(f'Sumo output directory: {output_dir}')
        self._config = read_config(config_path=config_path)
        self._output_dir = output_dir
        check_create_directory(self._output_dir)

    def get_config(self):
        return self._config

    def get_output_dir(self):
        return self._output_dir

    def _output_path_from_config_key(self, key: str):
        return Path(self._output_dir, self._config[key])

    def run_xml2csv(self, xml_path: Path) -> Path:
        csv_path = xml_path.with_suffix(KEY_CSV_SUFFIX)
        xml2csv_arguments = [f'"{xml_path}"',
                             f'--output "{csv_path}"']
        status = self._run_sumo_tool(name='xml' + os.sep + 'xml2csv.py',
                                     arguments=xml2csv_arguments)
        if status != 0:
            logging.warning(' ... transform failed')
            raise ValueError('Transformation of xml to csv failed.')

        return csv_path

    def netconvert(self, map_file_path: Path) -> Path:
        """Run SUMO's netconvert tool with the osm file map_file_path. The new
        network file, independent of whether it was created or existed 
        previously is returned as its relative path.

        Parameters
        ----------
        map_file_path : Path

        Returns
        -------
        Path
        """

        netconvert_bin_name = KEY_NETCONVERT_BIN
        net_file_path = self._output_path_from_config_key(KEY_NET_FILE)
        netconvert_arguments = [f'--osm-files "{map_file_path}"',
                                f'-o "{net_file_path}"',
                                '--geometry.remove',
                                '--geometry.avoid-overlap',
                                '--roundabouts.guess',
                                '--tls.join',
                                '--tls.uncontrolled-within',
                                '--tls.guess-signals',
                                '--tls.default-type actuated',
                                '--tls.no-mixed',
                                '--ramps.guess',
                                '--keep-edges.by-vclass passenger',
                                '--remove-edges.isolated',
                                '--no-internal-links',
                                '--no-turnarounds.except-deadend',
                                '--no-turnarounds.except-turnlane',
                                '--junctions.join',
                                '--junctions.join-dist 30',
                                '--osm.elevation'
                                ]

        self._run_sumo_binary(name=netconvert_bin_name,
                              arguments=netconvert_arguments)

        return net_file_path

    def polyconvert(self,
                     map_file_path: Path,
                     net_file_path: Path,
                     ) -> Path:
        """Run SUMO's polyconvert tool with the osm file map_file_path. The new
        file, independent whether it was created or existed previously
        is returned as its relative path.

        Parameters
        ----------
        map_file_path: Path
        net_file_path: Path

        Returns
        -------
        Path
        """

        pois_file_path = self._output_path_from_config_key(KEY_POIS_FILE)
        polyconvert_arguments = [f'--osm-files "{map_file_path}"',
                                 f'--net-file "{net_file_path}"',
                                 f'-o "{pois_file_path}"',
                                 '--no-warnings true'
                                 ]

        self._run_sumo_binary(name=KEY_POLYCONVERT_BIN,
                              arguments=polyconvert_arguments)

        return pois_file_path

    def run_sumo(self, arguments: Union[str, List[str]]):
        self._run_sumo_binary(name=KEY_SUMO_BIN,
                              arguments=arguments)

    def create_random_trips(self,
                            time_begin: float,
                            time_end: float,
                            net_file_path: Path,
                            period_new_vehicles: Optional[float] = None,
                            ) -> Tuple[Path, Path]:
        """Create random trips in a given time interval with a certain
        number of new vehicles randomly generated.

        Parameters
        ----------
        time_begin : float
        time_end : float
        period_new_vehicles : float, optional
            Defines the period length in seconds of new vehicles generated,
            in other words one new vehicle every ... seconds. If
            period_new_vehicle is None, the sumo default will be used.
        """

        random_trips_file_path = self._output_path_from_config_key(
            KEY_RANDOM_TRIPS_FILE)

        random_routes_file_path = self._output_path_from_config_key(
            KEY_RANDOM_ROUTES_FILE)

        opts = [f'-n "{net_file_path}"',
                f'-o "{random_trips_file_path}"',
                f'-r "{random_routes_file_path}"',
                '--validate',
                '--vclass passenger',
                r'--trip-attributes="type=\"private\""',
                '--intermediate 2',
                f'-b {time_begin}',
                f'-e {time_end}',
                ]
        if period_new_vehicles is not None:
            opts.append(f'-p {period_new_vehicles}')

        self._run_sumo_tool(name='randomTrips.py', arguments=opts)

        return random_trips_file_path, random_routes_file_path

    @staticmethod
    def _run_sumo_binary(name: str,
                         arguments: Union[str, List[str]],
                         ) -> int:
        """Run a certain SUMO binary with certain arguments in a terminal. It 
        returns the error status from the terminal (0-success, 1-failed).

        Parameters
        ----------
        name : str
        arguments : List[str]
        
        Returns
        -------
        int
        """

        sumo_bin_path = str(Path(PATH_SUMO_BIN, name))
        if isinstance(arguments, list):
            arguments = ' '.join(arguments)
        cmd = sumo_bin_path + ' ' + arguments

        logging.info(f"Starting Sumo binary {name.upper()} in {PATH_SUMO_BIN} "
                     f"with arguments:\n{arguments}.")

        return_code = run_command(cmd)

        if return_code == 0:
            logging.info(f"  {name.upper()} finished successfully.")
        else:
            raise RuntimeError(f"  {name.upper()} finished with errors.")

        return return_code

    @staticmethod
    def _run_sumo_tool(name: str,
                       arguments: Union[str, List[str]],
                       ) -> int:
        """
        Run a certain SUMO python tool with certain arguments in a terminal.
        It returns the error status from the terminal (0-success, 1-failed).

        Parameters
        ----------
        name : str
        arguments : List[str]
        
        Returns
        -------
        int
        """

        sumo_tool_path = str(Path(PATH_SUMO_TOOLS, name))
        if isinstance(arguments, list):
            arguments = ' '.join(arguments)
        cmd = f'{sys.executable} {sumo_tool_path} {arguments}'
        # sys.executable is the currently running python path

        logging.info(f"Starting Sumo tool {name.upper()} in "
                     f"{PATH_SUMO_TOOLS} with arguments:\n{arguments}.")

        return_code = run_command(cmd)

        if return_code == 0:
            logging.info(f"  {name.upper()} finished successfully.")
        else:
            raise RuntimeError(f"  {name.upper()} finished with errors.")

        return return_code
