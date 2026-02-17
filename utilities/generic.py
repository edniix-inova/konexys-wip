import re
import subprocess
import os
import contextlib
import yaml
import pickle
import zstandard as zstd
import numpy as np
import pandas as pd
import logging
from pyproj import Transformer  # use pyproj > 1.9.x
from typing import Union, Sequence, Tuple, Dict
from pathlib import Path

"""Generic functions

Functions:
- run_command 
- kill_java_subprocess
- list_processes
- delete_file
- find_within_parents
- get_repo_root
- read_config
- check_create_directory
- df_to_zstd
- zstd_to_df
- transformer
- clear_database
- dump_dataset_sample
- parse_rpyc_type

Context Manager:
- working_directory

"""

def run_command(cmd: str) -> int:
    """Run a certain command in a terminal. It returns the error status
    from the terminal (0-success, 1-failed).

    Parameters
    ----------
    cmd : str

    Returns
    -------
    int
    """
    p = subprocess.Popen(cmd,
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    out, err = p.communicate()
    try:
        encoding = 'UTF-8'
        logging.info(out.decode(encoding))
        logging.warning(err.decode(encoding))
    except UnicodeDecodeError:
        encoding = 'latin-1'
        logging.info(out.decode(encoding))
        logging.warning(err.decode(encoding))

    return_code = p.returncode
    if return_code != 0:
        p.kill()

    return return_code


def kill_java_subprocess(process_name_contains: str):
    """Try to kill java subprocesses that contains a certain string in its
    name. No error is raised if it fails

    Parameters
    ----------
    process_name_contains: str
    """
    if os.name == 'posix':
        try:
            out, err = \
                subprocess.Popen(["pgrep", "-f", f"{process_name_contains}"],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE).communicate()
            if len(out) > 0:
                logging.info(f'Killing process: {process_name_contains}')
                proc = subprocess.Popen(["pkill", "-f",
                                         f".*{process_name_contains}.*"],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE)
                out, err = proc.communicate()
                if len(out) > 0:
                    logging.info(out.decode())
                if len(err) > 0:
                    logging.error(err.decode())
                logging.info(f'Killed java process: {process_name_contains}')
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments: {1!r}"
            message = template.format(type(ex).__name__, ex.args[:])
            logging.error(message)
    else:
        try:
            output = subprocess.check_output(
                ' '.join(['"' + os.environ.get('JAVA_HOME')
                          + '/bin/jps"', '-m']), shell=False).decode()
            for line_process in re.split('\s(?=\d+)', output):  # noqa
                if process_name_contains in line_process.lower():
                    match_pid = re.match('\d+', line_process)  # noqa
                    kill_output = \
                        subprocess.check_output(' '.join(
                            ["taskkill",
                             '/F',
                             '/PID',
                             match_pid.group(0)]
                        ), shell=False).decode()
                    logging.info(kill_output)
        except Exception as ex:
            template = "An exception of type {0} occurred. Arguments: {1!r}"
            message = template.format(type(ex).__name__, ex.args[:])
            logging.warning(message)


def list_processes(process_name_contains='neo4j'):
    l_return = []
    try:
        output = subprocess.check_output(' '.join(['"' + os.environ.get(
            'JAVA_HOME') + '/bin/jps"', '-m']), shell=True).decode()
        for line_process in re.split('\s(?=\d+)', output):  # noqa
            if process_name_contains in line_process:
                l_return.append(line_process)
    except Exception as ex:
        template = "An exception of type {0} occurred. Arguments: {1!r}"
        message = template.format(type(ex).__name__, ex.args[:])
        logging.warning(message)
    return l_return


def delete_file(file_name: str):
    """Try to delete file. Pass upon failure

    Parameters
    ----------
    file_name: str
    """
    try:
        os.remove(file_name)
    except OSError:
        pass


# Context for dir
@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.
    """
    prev_cwd = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev_cwd)


def find_within_parents(target: str,
                        search_directory: Union[str, Path],
                        max_depth: int = 10
                        ):
    """Recursive function to find parent directory of "target".

    Search is done traversing upwards over the parents of the initial
    "search_directory" up to a maximum depth.

    Parameters
    ----------
    target: str
        Name to be found within a parent directory.
    search_directory: Union[str, Path]
        Starting path to perform the search.
    max_depth: int (optional)
        Maximum recursion level. Default value is 10.

    Returns
    -------
    str
        Absolute path to parent directory containing "target" element.
    """
    search_directory = Path(search_directory).absolute()
    dir_contents = [str(i.name) for i in search_directory.glob('*')]
    if target in dir_contents:
        target_dir = str(search_directory)
    elif max_depth == 0:
        raise FileNotFoundError('Could not find target.')
    else:
        target_dir = find_within_parents(target,
                                         search_directory.parent,
                                         max_depth=max_depth-1)

    return target_dir


def get_repo_root(parent_of: Union[str, Path] = '.git') -> str:
    """Get path to repo root in system.

    This function searches in the current directory and its parents for the
    name specified as <parent_of>. The directory containing it, is
    regarded as the repository root.

    Parameters
    ----------
    parent_of: Union[str, Path] (optional)
        name to search within parents

    Returns
    -------
    str
        parent path of searched element
    """
    # repo root is parent of the target directory
    repo_root = find_within_parents(parent_of, Path('.'))

    return repo_root


def read_config(config_path: Union[str, Path]) -> Union[Dict, None]:
    """Read yaml file and return as dictionary.

    Parameters
    ----------
    config_path: Union[str, Path]

    Returns
    -------
    Union[Dict, None]
    """
    with open(config_path, 'r') as config_file:
        try:
            return yaml.safe_load(config_file)
        except Exception as e:
            logging.warning('Could not read config file for module '
                            'dependencies: ', e)
            return None


def check_create_directory(path: Union[str, Path]):
    """Creates a directory if it does not already exist or the path points to a
    file. An error is raised if the path points to a file.

    Parameters
    ----------
    path : Path
    """
    if isinstance(path, str):
        path = Path(path)
    if not path.is_dir():
        if not path.is_file():
            path.mkdir(parents=True)
        else:
            raise FileExistsError(f'The path {path} points to a file.')


def df_to_zstd(data,
               output_file_path,
               max_size=4,
               threads=0,
               sort=True,
               verbose=True):
    # check if file already exists and try to delete
    if os.path.exists(output_file_path):
        try:
            logging.warning(f'File {output_file_path} already exists. It '
                            f'will be deleted and replaced by the new one.')
            os.remove(output_file_path)
        except Exception as e:
            raise e
    # compress data and dump into pickle
    size = data.memory_usage(index=True).sum() / 10 ** 9  # size in GB
    logging.info(f'Estimated memory usage of input data: {size:0.2f}GB')
    if sort:  # dataframe should be sorted but if it  was already done,
        # no need to repeat
        logging.info("Sorting data")
        data.sort_values(['vehicle_id', 'timestep_time'], inplace=True)
        logging.info("Sorting complete")
        data.reset_index(drop=True, inplace=True)
        logging.info("Index reset")
    vehicle_ids = data.loc[:, 'vehicle_id'].unique()
    nchunks = np.ceil(size / max_size)
    if nchunks > 1:
        logging.info(f'Data will be saved in chunks because maximum size '
                     f'allowed is {max_size}GB')
        chunks = np.array_split(vehicle_ids, nchunks)
        for num, chunk in enumerate(chunks):
            data_chunk = data.loc[data.loc[:, 'vehicle_id'].isin(chunk), :]
            dirname_len = len(os.path.dirname(output_file_path))
            file_name = output_file_path[dirname_len:].split('.')[
                0].lstrip(os.path.sep)
            new_file_name = output_file_path.replace(file_name,
                                                     file_name + f'_{num}')
            if new_file_name[-9:] != '.p.sumout':
                new_file_name = new_file_name + '.p.sumout'
                new_file_name = new_file_name.replace(".csv.sumout", "")
            with open(new_file_name, mode='wb') as f:
                cctx = zstd.ZstdCompressor(threads=threads)
                with cctx.stream_writer(f) as compressor:
                    pickle.dump(data_chunk, compressor, protocol=4)
                if verbose:
                    logging.info('Data chunk saved in file: ' + new_file_name)
    else:
        if output_file_path[-9:] != '.p.sumout':
            output_file_path = output_file_path + '.p.sumout'
            output_file_path = output_file_path.replace(".csv.sumout", "")
        with open(output_file_path, mode='wb') as f:
            cctx = zstd.ZstdCompressor(threads=threads)
            with cctx.stream_writer(f) as compressor:
                pickle.dump(data, compressor, protocol=4)
            if verbose:
                logging.info('Dataset saved in file: ' + output_file_path)

    return output_file_path


def zstd_to_df(file_path):
    if isinstance(file_path, str):
        with open(file_path, mode='rb') as f:
            cctx = zstd.ZstdDecompressor()
            with cctx.stream_reader(f) as decompressor:
                dataset = pickle.loads(decompressor.read())
        dataset.reset_index(drop=True, inplace=True)
        return dataset
    elif isinstance(file_path, list):
        files = list()
        for file_name in file_path:
            logging.info(f"loading {file_name}")
            with open(file_name, mode='rb') as f:
                cctx = zstd.ZstdDecompressor()
                with cctx.stream_reader(f) as decompressor:
                    dataset = pickle.loads(decompressor.read())
            files.append(dataset)
        logging.info("concatenating files")
        dataset = pd.concat(files)
        dataset.reset_index(drop=True, inplace=True)
        return dataset


original_system = 4326  # World Geodetic System 1984 (WGS84 - (lon, lat))
target_system = 3857  # Spherical Mercator for web services (OSM - (x, y))
transf = Transformer.from_crs(original_system, target_system,
                              always_xy=True).transform


def transformer(lon_lat: Sequence) -> Tuple:
    """Project geocoordinates to cartesian.

    Geocoordinates are expected ordered as (longitude, latitude) to be
    transformed to (x, y) in spherical mercator projection for web services.
    In terms of projection systems codes, we transform from system 4326 to
    system 3857.

    Parameters
    ----------
    lon_lat: Sequence
        Geocoordinate pair.

    Returns
    -------
    tuple
    """
    return transf(*lon_lat)


def clear_database(neo_wrapper):
    # remove Street data
    query1 = '''match (s:Street) where exists(s.cnt) set s += {
            vehicle_speed_mean: null,
            vehicle_speed_std: null,
            vehicle_acceleration_mean: null,
            vehicle_acceleration_std: null,
            cnt: null
            }'''
    # remove TRANSITION edges
    query2 = '''match (:Street)-[t:TRANSITION]->(:Street) set t += {
    transProb: 0, cntVehGlb: 0, transLogProb: null}'''
    # remove DRIVDATA edges
    query3 = '''match (:Node)-[d:DRIVDATA]-(:Node) delete d'''
    _ = neo_wrapper.run_for(0, 'send_query', query1)
    _ = neo_wrapper.run_for(0, 'send_query', query2)
    _ = neo_wrapper.run_for(0, 'send_query', query3)


def dump_dataset_sample(file_path=None, output=None):
    """
    Use this function to create dummy datasets.

    Here we read an actual dataset, figure out how many rows each vehicle
    track has to (arbitrarily) choose the longest
    one. Then the speed and acceleration columns are manipulated to create a
    new fake vehicle, and dump the concatenated
    tracks to a csv file.

    Parameters
    ----------
        file_path : string
            Path to file to be read. It should be a dataframe previously
            compressed using the df_to_pickle function.
        output : string
            Path to output file

    """

    repo_root = get_repo_root()
    if file_path is None:
        path_to_input_file = \
            os.path.join(repo_root,
                         'gvs',
                         'environment',
                         'road_terrain',
                         'sumo_tools',
                         'postproc_output',
                         'fcd_hour_5_20210629095953_neo4jInput_0.p.sumout')
    else:
        path_to_input_file = file_path

    if output is None:
        path_to_output_file = os.path.join(repo_root,
                                           'gvs',
                                           'environment',
                                           'road_terrain',
                                           'sumo_tools',
                                           'postproc_output',
                                           'fcd_sample.csv')
    else:
        path_to_output_file = output
    df = zstd_to_df(path_to_input_file)
    #  Look for the id of a vehicle track. Here we select one of the longest
    #  tracks.
    vehicle_id = \
        df.loc[:, ['timestep_time', 'vehicle_id']].groupby(
            by='vehicle_id').count() \
        .sort_values('timestep_time', ascending=False).index[0]

    df1 = df.loc[df.loc[:, 'vehicle_id'] == vehicle_id, :]
    d_speed = df1.loc[:, 'vehicle_speed'].diff()
    d_time = df1.loc[:, 'timestep_time'].diff()
    df1 = df1.assign(vehicle_acceleration=d_speed / d_time).bfill()
    df1.loc[:, 'timestep_time'] = df1.loc[:, 'timestep_time'] - 18000
    df1 = df1.head(10)
    df2 = df1.copy()
    df2.loc[:, 'vehicle_id'] = 'new_vehicle'
    #  Make the speed and acceleration of both vehicles differ an arbitrary
    #  factor. NOTE: this is not really realistic, since we do not adjust
    #  the coordinates accordingly (does this create any trouble??).
    df2.loc[:, ['vehicle_speed', 'vehicle_acceleration']] = \
        df2.loc[:, ['vehicle_speed', 'vehicle_acceleration']] * 3
    #  Create output dataframe.
    df = pd.concat([df1, df2], ignore_index=True)
    df.sort_values(by='timestep_time', ascending=True, inplace=True)
    df.to_csv(path_to_output_file, index=False)


def parse_rpyc_type(rpyc_data):
    if not isinstance(rpyc_data, dict):
        if isinstance(rpyc_data, list):
            list_data = []
            for j, k in enumerate(rpyc_data):
                list_data.append(parse_rpyc_type(k))
            return list_data
        else:
            if isinstance(rpyc_data, float):
                return float(rpyc_data)
            if isinstance(rpyc_data, int):
                return int(rpyc_data)
            else:
                return rpyc_data
    else:
        return {key: parse_rpyc_type(rpyc_data[key]) for key in rpyc_data}
