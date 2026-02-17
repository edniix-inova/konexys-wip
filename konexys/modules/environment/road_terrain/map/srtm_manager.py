import logging
import numpy as np
import os

from konexys.setup.paths import PATH_ELEVATION_DATA


class SrtmManager:
    """Management class of elevation data from srtm files."""
    SRTM_SAMPLES = 1201

    def __init__(self):
        self._elevation_data = dict()

    def get_elevation_data(self):
        return self._elevation_data

    def get_elevation_files(self):
        return self._elevation_data.keys()

    def calculate_elevation(self, lon: float, lat: float) -> int:
        """Returns the elevation in meters for a given (lon, lat) pair in °.

        Parameters
        ----------
        lon : float
            longitude in °
        lat : float
            latitude in °

        Returns
        -------
        int
        """

        hgt_file = self._get_elevation_file_name(lon, lat)

        # add file if it was not loaded yet
        if hgt_file not in self._elevation_data.keys():
            elevations = self._read_elevations_from_file(hgt_file=hgt_file)
            self._elevation_data[hgt_file] = elevations

        elevations = self._elevation_data[hgt_file]
        if elevations is not None:
            # calculate in which element of array it is
            lat_row = int(round((lat - int(lat)) * (self.SRTM_SAMPLES - 1), 0))
            lon_row = int(round((lon - int(lon)) * (self.SRTM_SAMPLES - 1), 0))

            elevation = elevations[self.SRTM_SAMPLES - 1 - lat_row, lon_row]
            elevation = elevation.astype(int)
        else:
            # if data not available because file not yet downloaded treat it
            # as void (as in SRTM documentation)
            elevation = -32768
        return elevation

    def _read_elevations_from_file(self, hgt_file: str) -> np.ndarray:
        """Read the elevation files and return its content as numpy array.

        Parameters
        ----------
        hgt_file : str

        Returns
        -------
        np.ndarray
        """

        hgt_file_path = os.path.join(PATH_ELEVATION_DATA, hgt_file)

        if os.path.isfile(hgt_file_path):
            logging.info(f'Reading elevation file: {hgt_file}')
            # HGT is 16bit signed integer(i2) - big endian(>)
            elevations = np.fromfile(
                file=hgt_file_path,
                dtype=np.dtype('>i2'),
                count=self.SRTM_SAMPLES * self.SRTM_SAMPLES
            )
            elevations = elevations.reshape(
                (self.SRTM_SAMPLES, self.SRTM_SAMPLES)
            )
        else:
            logging.warning(f'Elevation file not found: {hgt_file_path}')
            raise FileNotFoundError(f'Elevation file not found: {hgt_file_path}')
            # could try to download the missing data
            self._download_elevation_data()

        logging.info("Done")
        return elevations

    @staticmethod
    def _get_elevation_file_name(lon: float, lat: float) -> str:
        """Returns filename such as N27E086.hgt for a given (lon, lat) pair
        in °.

        Parameters
        ----------
        lon : float
            longitude in °
        lat : float
            latitude in °

        Returns
        -------
        str
        """

        ns = 'N' if lat >= 0 else 'S'
        ew = 'E' if lon >= 0 else 'W'

        hgt_file_name = "%(ns)s%(lat)02d%(ew)s%(lon)03d.hgt" % {
            'lat': abs(lat), 'lon': abs(lon), 'ns': ns, 'ew': ew}

        return hgt_file_name

    def _download_elevation_data(self):
        """Download elevation data if file is missing."""
        NotImplementedError
