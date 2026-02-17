import logging
import re
import shutil
from os.path import isfile
from pathlib import Path
from time import time, sleep
from typing import List, Union, Tuple

import requests
from lxml import etree

from konexys.modules.environment.road_terrain.map.srtm_manager import SrtmManager
from utilities.generic import check_create_directory
from utilities.generic import read_config

# keys for config file osm_manager.yaml
KEY_HEADER_TAGS = 'header_tags'
KEY_DATA_TAGS = 'data_tags'
KEY_DELETE_ELEM_ATTR = 'delete_elem_attr'
KEY_KEEP_ROAD_TYPES = 'keep_road_types'
KEY_OSM_FILE = 'osm_file'
KEY_OSM_HARDFILTERED_FILE = 'osm_hardfiltered_file'
KEY_OSM_SOFTFILTERED_FILE = 'osm_softfiltered_file'
KEY_OVERPASSAPI_URI = 'overpassapi_uri'


class OsmManager:
    """Management class to interact with the Open Street Map - Overpass API."""

    def __init__(self, config_path: Path, output_dir: Path):
        """

        Parameters
        ----------
        config_path : Path
        output_dir : Path
        """

        logging.info(f'OsmManager config file: {config_path}')
        logging.info(f'OsmManager output directory: {output_dir}')
        self._config = read_config(config_path=config_path)
        self._output_dir = output_dir
        # check/create output directory
        check_create_directory(path=self._output_dir)
        pass

    def get_config(self):
        return self._config

    def get_output_dir(self):
        return self._output_dir

    def download(self, bounding_box: Union[str, List[float]]) -> Path:
        """Downloads an Open Street Map from the Overpass Api into the
        osm_output_dir.

        Specifications are read from the config file. The
        ouput directory is created if it does not exist yet. If the output
        file exists already, the download is skipped. There is no check
        whether the output file corresponds to the config file.

        Parameters
        ----------
        bounding_box: List[float]

        Returns
        -------
        output_path: Path
        """

        logging.info('Downloading open street map data from overpass.')

        osm_path = Path(self._output_dir, self._config[KEY_OSM_FILE])

        overpassapi = self._config[KEY_OVERPASSAPI_URI]

        if isinstance(bounding_box, str):
            south, west, north, east = list(map(float, bounding_box.split(",")))
        else:
            assert len(bounding_box) == 4
            south, west, north, east = bounding_box

        query = f"(node({south},{west},{north},{east});<;); out meta;"
        logging.info(f'Requesting OSM data from overpass with: {query}')

        retries = 0
        # Try the download 10 times in case of timeouts or similar
        while retries < 10:
            retries += 1
            r = requests.post(overpassapi, data={"data": query})
            logging.info(f"{retries}. request with status {r.status_code}")
            if r.status_code == 200:
                break
            else:
                sleep(60)     # wait for 1 minute

        r.raise_for_status()
        logging.info("Done")

        # Write data
        logging.info(f"Writing map data to file: {osm_path}")
        with open(osm_path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=128):
                fd.write(chunk)
        logging.info("Done")

        return osm_path

    def copy(self, original_osm_path: Path) -> Path:
        """Copies a previously downloaded osm file. This is an alternative
        to the overpass download.

        Parameters
        ----------
        original_osm_path: Path

        Returns
        -------
        output_path: Path
        """

        osm_path = Path(self._output_dir, self._config[KEY_OSM_FILE])
        logging.info(f'Copying open street map file {original_osm_path} to '
                     f'{osm_path}')
        shutil.copy(original_osm_path, osm_path)
        return osm_path

    def process(self, osm_download_path: Path) -> Tuple[Path, Path]:
        """ Applies a soft and a hard filter to the orignial osm file and
        adds elevation data.
        """

        osm_soft_filter_path = \
            self._apply_soft_filter_add_elevation(osm_download_path)
        osm_hard_filter_path = self._apply_hard_filter(osm_soft_filter_path)
        return osm_soft_filter_path, osm_hard_filter_path

    def _apply_soft_filter_add_elevation(self,
                                         osm_download_path: Path) -> Path:
        """Applies the soft filter and adds elevation data."""
        osm_soft_filter_path = Path(self._output_dir,
                                    self._config[KEY_OSM_SOFTFILTERED_FILE])
        header_tags = self._config[KEY_HEADER_TAGS]
        data_tags = self._config[KEY_DATA_TAGS]
        keep_road_types = self._config[KEY_KEEP_ROAD_TYPES]
        delete_elem_attr = self._config[KEY_DELETE_ELEM_ATTR]

        if not isfile(osm_download_path):
            raise FileNotFoundError(f'Could not find original map '
                                    f'file: {osm_download_path}.')

        logging.info("Begin mild filtering of unwanted XML elements and "
                     "insert elevation values in OSM file.")

        t0 = time()
        elevations = SrtmManager()

        # read map file with xml filters with header and data tags only
        context = etree.iterparse(source=osm_download_path,
                                  events=('end',),
                                  tag=header_tags + data_tags,
                                  remove_blank_text=True,
                                  )

        # Copy the header (first 2 lines)
        with open(osm_download_path) as f:
            head = [next(f) for _ in range(2)]
        # get original encoding from map file
        osm_encoding = re.findall(r'ncoding="(.+)"', head[0])[0]
        with open(osm_soft_filter_path, 'w', encoding=osm_encoding) as f:
            for line in head:
                f.write(line)

        node_counter = 0
        with open(osm_soft_filter_path, 'ab') as f:
            for _, elem in context:
                if elem.tag == 'way':
                    etree.strip_attributes(elem, delete_elem_attr)
                    test_way = [child.attrib.get('k') == 'highway'
                                and child.attrib.get('v') in keep_road_types
                                for child in elem]
                    if any(test_way):
                        test1 = lambda x: (
                                (x.attrib.get('k') == 'highway'
                                 and x.attrib.get('v') in keep_road_types)
                                or (x.tag == 'nd')
                                or (x.attrib.get('k') in
                                    ['maxspeed', 'name', 'oneway'])
                        )
                        keep_ch = [child for child in elem if test1(child)]
                        etree.strip_elements(elem, 'tag')
                        for ch in reversed(keep_ch):
                            elem.insert(0, ch)
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                elif elem.tag == 'node':
                    node_counter += 1
                    etree.strip_attributes(elem, delete_elem_attr)
                    test_bus_stop = [(c.get('k') == 'bus'
                                      and c.get('v') == 'yes')
                                     for c in elem.getchildren()]
                    test_traffic_signal = [(c.get('v') == 'traffic_signals')
                                           for c in elem.getchildren()]
                    if any(test_bus_stop) or any(test_traffic_signal):
                        lat, lon = float(elem.attrib['lat']), float(
                            elem.attrib['lon'])
                        elev = elevations.calculate_elevation(lon, lat)
                        if elev > -1000:
                            elem.set('height', str(elev))
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                    else:
                        etree.strip_elements(elem, 'tag')
                        lat = float(elem.attrib['lat'])
                        lon = float(elem.attrib['lon'])
                        elev = elevations.calculate_elevation(lon, lat)
                        if elev > -1000:
                            elem.set('height', str(elev))
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                elif elem.tag == 'relation':
                    etree.strip_attributes(elem, delete_elem_attr)
                    test_busroute = [(c.get('k') == 'route'
                                      and c.get('v') == 'bus')
                                     for c in elem.getchildren()]
                    if any(test_busroute):
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                    continue  # Why continue in relation and not clear_element?
                else:
                    f.write(etree.tostring(elem,
                                           encoding=osm_encoding,
                                           pretty_print=True))
                self._clear_delete_element(elem)

        # We have to manually close the "map" tag
        with open(osm_soft_filter_path, 'a', encoding=osm_encoding) as f:
            f.write(r'</osm>')

        del context
        logging.info("Filtering completed in {:.2f} s.".format(time() - t0))

        return osm_soft_filter_path

    def _apply_hard_filter(self, osm_soft_filter_path: Path) -> Path:
        """Applies a hard filter on the osm file."""
        osm_hard_filter_path = Path(self._output_dir,
                                    self._config[KEY_OSM_HARDFILTERED_FILE])
        header_tags = self._config[KEY_HEADER_TAGS]
        data_tags = self._config[KEY_DATA_TAGS]
        keep_road_types = self._config[KEY_KEEP_ROAD_TYPES]
        delete_elem_attr = self._config[KEY_DELETE_ELEM_ATTR]

        if not isfile(osm_soft_filter_path):
            raise FileNotFoundError(f'Could not find soft-filtered map'
                                    f'file: {osm_soft_filter_path}.')

        logging.info("Begin strict filtering of "
                     "unwanted XML elements in OSM file.")

        t0 = time()

        # Copy the header (first 2 lines)
        with open(osm_soft_filter_path) as f:
            head = [next(f) for _ in range(2)]
        # get original encoding from map file
        osm_encoding = re.findall(r'ncoding="(.+)"', head[0])[0]
        with open(osm_hard_filter_path, 'w', encoding=osm_encoding) as f:
            for line in head:
                f.write(line)

        # Iterative writing of map file
        context = etree.iterparse(osm_soft_filter_path,
                                  events=('end',),
                                  tag=header_tags + data_tags,
                                  remove_blank_text=True)
        with open(osm_hard_filter_path, 'ab') as f:
            for _, elem in context:
                if elem.tag == 'way':
                    etree.strip_attributes(elem, delete_elem_attr)
                    test_way = [child.attrib.get('k') == 'highway'
                                and child.attrib.get('v') in keep_road_types
                                for child in elem]
                    if any(test_way):
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                elif elem.tag == 'node':
                    etree.strip_attributes(elem, delete_elem_attr)
                    test_node = [(c.get('k') == 'amenity')
                                 for c in elem.getchildren()]
                    if any(test_node):
                        # if there is school info in the
                        # node skip it. otherwise, delete info and write to
                        # filtered file
                        continue
                    else:
                        etree.strip_elements(elem, 'tag')
                        f.write(etree.tostring(elem,
                                               encoding=osm_encoding,
                                               pretty_print=True))
                elif elem.tag == 'relation':
                    continue
                else:
                    f.write(etree.tostring(elem,
                                           encoding=osm_encoding,
                                           pretty_print=True))
                self._clear_delete_element(elem)
        # We have to manually close the "map" tag
        with open(osm_hard_filter_path, 'a', encoding=osm_encoding) as f:
            f.write(r'</osm>')

        del context
        logging.info("Filtering completed in {:.2f} s.".format(time() - t0))

        return osm_hard_filter_path

    @staticmethod
    def _clear_delete_element(elem):
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]
