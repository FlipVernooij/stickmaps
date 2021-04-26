import math
from enum import Enum

from PySide6.QtCore import QPointF
from haversine import haversine, Unit  # we should remove this package.


# EQUATOR_LENGTH_METERS = 40075004
# EQUATOR_RADIUS_METERS = 6378137.0
# POLAR_RADIUS_METERS = 6356752.3
# The International Union of Geodesy and Geophysics (IUGG) defines the mean radius (denoted R1) to be
from Config.Constants import SCENE_DEFAULT_ZOOM, DEGREES_NE

WORLD_MEAN_RADIUS_METERS = 6371008.8


class DistanceUnit(Enum):
    KILOMETERS = 'km'
    METERS = 'm'
    MILES = 'mi'
    NAUTICAL_MILES = 'nmi'
    FEET = 'ft'
    INCHES = 'in'

    # Unit values taken from http://www.unitconversion.org/unit_converter/length.html
    _CONVERSIONS = {
            'km': 1.0,
            'm': 1000.0,
            'mi': 0.621371192,
            'nmi': 0.539956803,
            'ft': 3280.839895013,
            'in': 39370.078740158
        }

    @classmethod
    def convert(cls, from_value: float, from_unit, to_unit):
        f = cls._CONVERSIONS[from_unit]
        t = cls._CONVERSIONS[to_unit]
        f_value = from_value / f # value in km
        return (f_value * t)


class TranslateCoordinates:

    """
        lat_lng = latitude/longitude, WGS84 coordinate, EPSG:4326
        xy = EPSG:900913, references to both scene coordinate as google world-coordinate (Spherical Mercator map projection coordinates (google & bing?)  EPSG.io
        p_xy = The coordinate of a pixel within the ViewPort (and not scene!), we should try to avoid this.

        check: https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection/


        world coordinates are the same as pixel-coordinates at zoom level 0.
        Yet they are of type FLOAT so you can have a coordinate far more specific then a pixel on a 256x256 sized world map.
        As the world map is 256x256, the world coordinates can not be greater then 256x256. Map precision is accomplished by the float value.
    """


    def latlng_at_distance(self, from_latlng: QPointF, distance_in_meters: float, heading_degrees: float) -> QPointF:
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
            distance = distance_in_meters / WORLD_MEAN_RADIUS_METERS
            heading = math.radians(heading_degrees)
            from_latitude = math.radians(from_latlng.x())
            from_longitude = math.radians(from_latlng.y())
            cos_distance = math.cos(distance)
            sin_distance = math.sin(distance)
            sin_from_latitude = math.sin(from_latitude)
            cos_from_latitude = math.cos(from_latitude)
            sin_latitude = cos_distance * sin_from_latitude + sin_distance * cos_from_latitude * math.cos(heading)
            distance_longitude = math.atan2(sin_distance * cos_from_latitude * math.sin(heading),
                                            cos_distance - sin_from_latitude * sin_latitude)
            latitude = math.degrees(math.asin(sin_latitude))
            longitude = math.degrees(from_longitude + distance_longitude)
            return QPointF(latitude, longitude)

    def xy_2_latlng(self, xy: QPointF) -> QPointF:
        """
            convert Google-style Mercator tile coordinate to (lat, lng)
            @see https://github.com/hrldcpr/mercator.py
        """
        x = xy.x()
        y = xy.y()

        lat_rad = math.pi - 2 * math.pi * y / math.pow(2, SCENE_DEFAULT_ZOOM)
        lat_rad = 2 * math.atan(math.exp(lat_rad)) - math.pi / 2
        lat = math.degrees(lat_rad)

        lng = -180.0 + 360.0 * x / math.pow(2, SCENE_DEFAULT_ZOOM)

        ret = QPointF(lat, lng)
        # ret.setX(lat)
        # ret.setY(lng)
        return ret

    def latlng_2_xy(self, latlng: QPointF) -> QPointF:
        lat = latlng.x()
        lng = latlng.y()

        siny = math.sin((lat * math.pi) / 180);
        # Truncating to 0.9999 effectively limits latitude to 89.189. This is
        # about a third of a tile past the edge of the world tile.
        siny = min(max(siny, -0.9999), 0.9999);

        y = 256 * (0.5 + lng / 360)
        x = 256 * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi))
        return QPointF(y, x)

    def latlng_2_mercator(self, latlng: QPointF) -> QPointF:
        """
            convert lat/lng to Google-style Mercator tile coordinate (x, y)
            @see https://github.com/hrldcpr/mercator.py
        """
        lat = latlng.x()
        lng = latlng.y()


        lat_rad = math.radians(lat)
        lat_rad = math.log(math.tan((lat_rad + math.pi / 2) / 2))

        x = math.pow(2, SCENE_DEFAULT_ZOOM) * (lng + 180.0) / 360.0
        y = math.pow(2, SCENE_DEFAULT_ZOOM) * (math.pi - lat_rad) / (2 * math.pi)
        ret = QPointF(x, y)
        return ret

    "Caching dict"
    _cache_xy_per_km_at = {}

    def xy_per_km_at(self, latlng: QPointF) -> float:
        """
            Returns the amount of xy points per kilometer.
            The lat-lng is required to take into account the Mercator projection.

        """
        cache_key = f'lat_{latlng.x()}-lng_{latlng.y()}'
        try:
            return self._cache_xy_per_km_at[cache_key]
        except KeyError:
            xy = self.latlng_2_xy(latlng)
            # @todo is DEGREES_NE the best to chose?
            to_latlng = self.latlng_at_distance(latlng, 1000, DEGREES_NE)
            to_xy = self.latlng_2_xy(to_latlng)

            diff = to_xy - xy
            self._cache_xy_per_km_at[cache_key] = diff.x() + diff.y()
        return self._cache_xy_per_km_at[cache_key]

#
# class CalcDistance:
#     """
#         We have the following grid units
#             - lat/long
#             - google_maps xy    "World Geodetic System WGS84"
#             - pixel xy at zoom-level
#             - scene xy  "World Geodetic System WGS84"
#             - view xy
#     """
#
#     def __init__(self, lat_lng: QPointF, zoom_level: float):
#         self.lat_lng = lat_lng
#         self.zoom_level = zoom_level
#
#     def between_latlng(self, from_lat_lng: QPointF, to_lat_lng: QPointF = None, unit: DistanceUnit=DistanceUnit.METERS) -> float:
#         if to_lat_lng is None:
#             to_lat_lng = self.lat_lng
#
#         return self._haversine(from_lat_lng, to_lat_lng, unit)
#
#     def between_xy(self, from_xy: QPointF, to_xy: QPointF = None, unit=DistanceUnit.METERS) -> float:
#         pass
#
#     def xy_2_latlng(self, xy: QPointF) -> QPointF:
#         """
#             convert Google-style Mercator tile coordinate to (lat, lng)
#             @see https://github.com/hrldcpr/mercator.py
#         """
#         x = xy.x()
#         y = xy.y()
#
#         lat_rad = math.pi - 2 * math.pi * y / math.pow(2, self.zoom_level)
#         lat_rad = 2 * math.atan(math.exp(lat_rad)) - math.pi / 2
#         lat = math.degrees(lat_rad)
#
#         lng = -180.0 + 360.0 * x / math.pow(2, self.zoom_level)
#
#         ret = QPointF()
#         ret.setX(lat)
#         ret.setY(lng)
#         return ret
#
#     def _haversine(self, from_latlng: QPointF, to_latlng: QPointF, unit: DistanceUnit) -> float:
#         """ Calculate the great-circle distance between two points on the Earth surface.
#
#         Takes two 2-tuples, containing the latitude and longitude of each point in decimal degrees,
#         and, optionally, a unit of length.
#
#         :param point1: first point; tuple of (latitude, longitude) in decimal degrees
#         :param point2: second point; tuple of (latitude, longitude) in decimal degrees
#         :param unit: a member of haversine.Unit, or, equivalently, a string containing the
#                      initials of its corresponding unit of measurement (i.e. miles = mi)
#                      default 'km' (kilometers).
#
#         Example: ``haversine((45.7597, 4.8422), (48.8567, 2.3508), unit=Unit.METERS)``
#
#         Precondition: ``unit`` is a supported unit (supported units are listed in the `Unit` enum)
#
#         :return: the distance between the two points in the requested unit, as a float.
#
#         The default returned unit is kilometers. The default unit can be changed by
#         setting the unit parameter to a member of ``haversine.Unit``
#         (e.g. ``haversine.Unit.INCHES``), or, equivalently, to a string containing the
#         corresponding abbreviation (e.g. 'in'). All available units can be found in the ``Unit`` enum.
#         """
#
#         # unpack latitude/longitude
#         lat1, lng1 = from_latlng.toTuple()
#         lat2, lng2 = to_latlng.toTuple()
#
#         # convert all latitudes/longitudes from decimal degrees to radians
#         lat1 = math.radians(lat1)
#         lng1 = math.radians(lng1)
#         lat2 = math.radians(lat2)
#         lng2 = math.radians(lng2)
#
#         # calculate haversine
#         lat = lat2 - lat1
#         lng = lng2 - lng1
#         d = math.sin(lat * 0.5) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lng * 0.5) ** 2
#
#         return 2 * DistanceUnit.convert(MEAN_RADIUS_METERS, DistanceUnit.METERS, unit) * math.asin(math.sqrt(d))
