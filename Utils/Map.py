import datetime
import logging
import pathlib
import shutil

import pyIGRF
import requests
from PySide6.QtCore import QPointF, Qt, QPoint
import math

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem

from Config.Constants import GOOGLE_STATIC_MAPS_URL, GOOGLE_STATIC_MAPS_API_KEY, GOOGLE_MAPS_SCALING, \
    APPLICATION_CACHE_DIR
from Utils.Settings import Preferences


class GeoMixin:
    WORLD_TILE_SIZE = 256

    def xy_2_latlng(self, xy: QPointF, zoom: int) -> QPointF:
        """
            convert Google-style Mercator tile coordinate to (lat, lng)
            @see https://github.com/hrldcpr/mercator.py
        """
        x = xy.x()
        y = xy.y()

        lat_rad = math.pi - 2 * math.pi * y / math.pow(2, zoom)
        lat_rad = 2 * math.atan(math.exp(lat_rad)) - math.pi / 2
        lat = math.degrees(lat_rad)

        lng = -180.0 + 360.0 * x / math.pow(2, zoom)

        ret = QPointF()
        ret.setX(lat)
        ret.setY(lng)
        return ret

    def latlng_2_xy(self, latlng: QPointF, zoom: int):
        """
            convert lat/lng to Google-style Mercator tile coordinate (x, y)
            @see https://github.com/hrldcpr/mercator.py
        """
        lat = latlng.x()
        lng = latlng.y()

        lat_rad = math.radians(lat)
        lat_rad = math.log(math.tan((lat_rad + math.pi / 2) / 2))

        x = math.pow(2, zoom) * (lng + 180.0) / 360.0
        y = math.pow(2, zoom) * (math.pi - lat_rad) / (2 * math.pi)
        ret = QPointF()
        ret.setX(x)
        ret.setY(y)
        return ret

    def xy_value_for_pixels(self, pixels: int):
        return pixels / self.WORLD_TILE_SIZE

    """ UNTESTED, CHECK THIS!!"""
    def azimuth_to_latlng(self, location_start: QPointF, length: float, azimuth: float) -> QPointF:
        """
        This is the code used by google map (SphericalUtil.java)

        https://stackoverflow.com/questions/8586635/convert-meters-to-latitude-longitude-from-any-point


        Whenever the API needs to translate a location in the world to a location on a map, it first translates latitude and longitude values into a world coordinate.
        The API uses the Mercator projection to perform this translation.

        Latitude and longitude values, which reference a point on the world uniquely. (Google uses the World Geodetic System WGS84 standard.)

        :param location_start:
        :param length:
        :param azimuth:
        :return:
        """
        distance = length / self.EARTH_RADIUS
        azimuth = self._ajust_earth_magnetic_field(location_start, azimuth)
        heading = math.radians(azimuth)
        from_latitude = math.radians(location_start.getX())
        from_longitude = math.radians(location_start.getY())
        cos_distance = math.cos(distance)
        sin_distance = math.sin(distance)
        sin_from_latitude = math.sin(from_latitude)
        cos_from_latitude = math.cos(from_latitude)
        sin_latitude = cos_distance * sin_from_latitude + sin_distance * cos_from_latitude * math.cos(heading)
        distance_longitude = math.atan2(sin_distance * cos_from_latitude * math.sin(heading), cos_distance - sin_from_latitude * sin_latitude)
        return QPointF(xpos=math.asin(sin_latitude), ypos=from_longitude + distance_longitude)

    def _ajust_earth_magnetic_field(self, lat_lng: QPointF, azimuth: float, depth: float = 0,
                                    year: int = 2020) -> float:
        """
            @todo This sort of breaks quick and dirty coordinate calculations
                    I should inspect this a bit deeper, see what the actual variations are... it would be great to forget about this in loop-closures ect.

            I do think that manual compasses already have the degree offset, so we should only do this for a specified set of devices.
            We should probably make this a setting in preferences or something...?

            :param lat_long:
            :param azimuth:
            :param depth:
            :param year:
            :return:
        """
        result = pyIGRF.igrf_value(lat_lng.getX(), lat_lng.getY(), alt=depth, year=float(year))
        # @todo Do something with the result and the azimuth...
        # https://pypi.org/project/pyIGRF/
        self.log.info('We are NOT calculating magnetic variation of the earth. ')
        return azimuth


class FileFetchMixin:

    def _request_image(self, latlng: QPointF, zoom: int, map_type: str = 'satellite', provider: str = 'google'):
        lat = latlng.x()
        lng = latlng.y()

        url = self._get_url(provider, lat, lng, zoom, map_type)
        file_name = self._get_cache_filename(lat, lng, zoom, map_type)
        file = pathlib.Path(file_name)
        self.log.debug(f'requesting maps image: url: {url} cache_file: {file_name}')
        if not file.exists():
            self.log.debug(f'Cache file does not exist, requesting')
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                with open(file_name, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            else:
                self.log.error(f"Failed fetching googlemaps image for: {url}")
        else:
            self.log.debug(f'Cache file found')

        return file_name

    def _get_url(self, provider: str, lat: float, lng: float, zoom: int, map_type: str = 'satellite'):
        if provider == 'google':
            return f'{GOOGLE_STATIC_MAPS_URL}' \
                   f'?key={GOOGLE_STATIC_MAPS_API_KEY}' \
                   f'&center={lat},{lng}' \
                   f'&scaling={Preferences.get("google_maps_scaling", GOOGLE_MAPS_SCALING, int)}' \
                   f'&zoom={zoom}' \
                   f'&maptype={map_type}' \
                   f'&size=640x640' \
                   f'&format=jpg'
        else:
            self.log.error('Provider {provider} not found, try again')

    def _get_cache_filename(self, lat: float, lng: float, zoom: int, map_type: str = 'satellite'):
        return f'{Preferences.get("application_cache_dir", APPLICATION_CACHE_DIR, str)}/gsm_{map_type}{lat},{lng}_{zoom}.jpg'



class OverlayGoogleMaps(GeoMixin, FileFetchMixin):

    TILE_NORTH = 360
    TILE_NORTH_EAST = 45
    TILE_EAST = 90
    TILE_SOUTH_EAST = 135
    TILE_SOUTH = 180
    TILE_SOUTH_WEST = 225
    TILE_WEST = 270
    TILE_NORTH_WEST = 315


    def __init__(self, parent):
        self.parent = parent
        self.log = logging.getLogger(__name__)

        self.zoom = 20
        self.tile_height = 640
        self.tile_width = 640

    def get_tile(self,  lat_lng: QPointF, offset_item: QPoint = None) -> QGraphicsPixmapItem:
        """
            @todo I am manually downscalling the images from 640 to 320 for some reason.
                    This might have todo with the fact that I DO NOT have a highress screen.. but am requesting a 2x image.
        :param lat_lng:
        :param offset_item:
        :return:
        """
        image = self._request_image(lat_lng, self.zoom)
        pixmap = QPixmap.fromImage(image).scaled(self.tile_width / 2, self.tile_height / 2, Qt.KeepAspectRatioByExpanding)
        item = QGraphicsPixmapItem(pixmap)

        if offset_item is not None:
            item.setY(offset_item.y() / 2)
            item.setX(offset_item.x() / 2)

        return item

    def get_surrounding_tile_heading(self, lat_lng: QPointF, heading: int):
        """
        This should return the lat/lng of the next tile to the "heading" (North)
        So it calculates the lat/lng of x+0 pixels and y+640 pixels.
        """
        xy = self.latlng_2_xy(lat_lng, self.zoom)
        offset = QPoint(0, 0)
        map_height = self.xy_value_for_pixels(self.tile_height)
        map_width = self.xy_value_for_pixels(self.tile_width)

        if heading in (self.TILE_NORTH, self.TILE_NORTH_EAST, self.TILE_NORTH_WEST):
            xy.setY(xy.y()+(map_height * -1))
            offset.setY(self.tile_height * -1)
        if heading in (self.TILE_SOUTH, self.TILE_SOUTH_EAST, self.TILE_SOUTH_WEST):
            xy.setY(xy.y() + map_height)
            offset.setY(self.tile_height)
        if heading in (self.TILE_EAST, self.TILE_NORTH_EAST, self.TILE_SOUTH_EAST):
            xy.setX(xy.x() + (map_width * -1))
            offset.setX(self.tile_width * -1)
        if heading in (self.TILE_WEST, self.TILE_NORTH_WEST, self.TILE_SOUTH_WEST):
            xy.setX(xy.x() + map_width)
            offset.setX(self.tile_width)

        latlng = self.xy_2_latlng(xy, self.zoom)

        return self.get_tile(latlng, offset)






    

"""
pyIGRF  -> 
            We can use this package to calculate the magnetic difference arround the earth.
            Ariane has some kint of a manual method for this in com.arianesline.IGRF
            Python has a package for it which is awesome.
            
            
"""
class StationItem:
    """
        This class generates the location of the next station.
    """
    EARTH_RADIUS = 6371009.0  # meters

    def __init__(self, current_location: QPointF, import_station_row: dict, year: int):
        self.current_location = current_location
        self.next_station = import_station_row
        #self.geo_tool = GeoTools()
        self.lat_lng = self.geo_tools.heading_to_lat_long(current_location, import_station_row['length_out'], year)

    def get_longitude(self) -> float:
        return 0

    def get_latitude(self) -> float:
        return 0

    def get_point(self):
        return self.lat_lng

