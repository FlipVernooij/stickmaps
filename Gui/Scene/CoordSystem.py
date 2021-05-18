import math

from PySide6.QtCore import QPointF, QRect, QSizeF, QSize

from Config.Constants import SCENE_DEFAULT_ZOOM, DEGREES_NE, SCENE_MAP_TILE_SIZE, DEGREES_NW

EQUATOR_LENGTH_METERS = 40075004
EQUATOR_RADIUS_METERS = 6378137.0
POLAR_RADIUS_METERS = 6356752.3
# # The International Union of Geodesy and Geophysics (IUGG) defines the mean radius (denoted R1) to be
WORLD_MEAN_RADIUS_METERS = 6371008.8

"""
    @todo mercator doesn't use the mean radius but the equator radius.
"""
class TranslateCoordinates:

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mercator = GlobalMercator()

    @property
    def xy_per_km(self) -> float:
        return 6698.324242043919

    @property
    def xy_per_m(self) -> float:
        # https: // www.maptiler.com / google - maps - coordinates - tile - bounds - projection /
        # @todo yet I think this might have to be lat/lng depended?
        meters_per_pixel = 0.149291071
        pixels_per_meter = 6.6983242420439195  # 1 / 0.149291071
        return 6.6983242420439195

    def  latlng_2_xy(self, latlng: QPointF) -> QPointF:
        mx, my = self.mercator.LatLonToMeters(latlng.x(), latlng.y())
        px, py = self.mercator.MetersToPixels(mx, my)
        return QPointF(px, py)

    def xy_2_latlng(self, xy: QPointF) -> QPointF:
        mx, my = self.mercator.PixelsToMeters(xy.x(), xy.y())
        lat, lng = self.mercator.MetersToLatLon(mx, my)
        return QPointF(lat, lng)

    def xy_rect_with_center_at(self, latlng: QPointF, size_in_meters: QSizeF) -> QRect:
        # center_xy = self.latlng_2_xy(latlng)
        half_diameter = math.sqrt(math.pow(size_in_meters.width(), 2) + math.pow(size_in_meters.height(), 2)) / 2
        top_left_latlng = self.latlng_at_distance(latlng, half_diameter, DEGREES_NW)
        top_left_xy = self.latlng_2_xy(top_left_latlng)


        m_xy = self.xy_per_m
        rect = QRect(top_left_xy.toPoint(), QSize(size_in_meters.width()*m_xy, size_in_meters.height()*m_xy))
        return rect

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


class GlobalMercator(object):
    """
    TMS Global Mercator Profile
    ---------------------------
    Functions necessary for generation of tiles in Spherical Mercator projection,
    EPSG:900913 (EPSG:gOOglE, Google Maps Global Mercator), EPSG:3785, OSGEO:41001.
    Such tiles are compatible with Google Maps, Microsoft Virtual Earth, Yahoo Maps,
    UK Ordnance Survey OpenSpace API, ...
    and you can overlay them on top of base maps of those web mapping applications.

    Pixel and tile coordinates are in TMS notation (origin [0,0] in bottom-left).
    What coordinate conversions do we need for TMS Global Mercator tiles::
         LatLon      <->       Meters      <->     Pixels    <->       Tile
     WGS84 coordinates   Spherical Mercator  Pixels in pyramid  Tiles in pyramid
         lat/lon            XY in metres     XY pixels Z zoom      XYZ from TMS
        EPSG:4326           EPSG:900913
         .----.              ---------               --                TMS
        /      \     <->     |       |     <->     /----/    <->      Google
        \      /             |       |           /--------/          QuadTree
         -----               ---------         /------------/
       KML, public         WebMapService         Web Clients      TileMapService
    What is the coordinate extent of Earth in EPSG:900913?
      [-20037508.342789244, -20037508.342789244, 20037508.342789244, 20037508.342789244]
      Constant 20037508.342789244 comes from the circumference of the Earth in meters,
      which is 40 thousand kilometers, the coordinate origin is in the middle of extent.
      In fact you can calculate the constant as: 2 * math.pi * 6378137 / 2.0
      $ echo 180 85 | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:900913
      Polar areas with abs(latitude) bigger then 85.05112878 are clipped off.
    What are zoom level constants (pixels/meter) for pyramid with EPSG:900913?
      whole region is on top of pyramid (zoom=0) covered by 256x256 pixels tile,
      every lower zoom level resolution is always divided by two
      initialResolution = 20037508.342789244 * 2 / 256 = 156543.03392804062
    What is the difference between TMS and Google Maps/QuadTree tile name convention?
      The tile raster itself is the same (equal extent, projection, pixel size),
      there is just different identification of the same raster tile.
      Tiles in TMS are counted from [0,0] in the bottom-left corner, id is XYZ.
      Google placed the origin [0,0] to the top-left corner, reference is XYZ.
      Microsoft is referencing tiles by a QuadTree name, defined on the website:
      http://msdn2.microsoft.com/en-us/library/bb259689.aspx
    The lat/lon coordinates are using WGS84 datum, yeh?
      Yes, all lat/lon we are mentioning should use WGS84 Geodetic Datum.
      Well, the web clients like Google Maps are projecting those coordinates by
      Spherical Mercator, so in fact lat/lon coordinates on sphere are treated as if
      the were on the WGS84 ellipsoid.

      From MSDN documentation:
      To simplify the calculations, we use the spherical form of projection, not
      the ellipsoidal form. Since the projection is used only for map display,
      and not for displaying numeric coordinates, we don't need the extra precision
      of an ellipsoidal projection. The spherical projection causes approximately
      0.33 percent scale distortion in the Y direction, which is not visually noticable.
    How do I create a raster in EPSG:900913 and convert coordinates with PROJ.4?
      You can use standard GIS tools like gdalwarp, cs2cs or gdaltransform.
      All of the tools supports -t_srs 'epsg:900913'.
      For other GIS programs check the exact definition of the projection:
      More info at http://spatialreference.org/ref/user/google-projection/
      The same projection is degined as EPSG:3785. WKT definition is in the official
      EPSG database.
      Proj4 Text:
        +proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0
        +k=1.0 +units=m +nadgrids=@null +no_defs
      Human readable WKT format of EPGS:900913:
         PROJCS["Google Maps Global Mercator",
             GEOGCS["WGS 84",
                 DATUM["WGS_1984",
                     SPHEROID["WGS 84",6378137,298.2572235630016,
                         AUTHORITY["EPSG","7030"]],
                     AUTHORITY["EPSG","6326"]],
                 PRIMEM["Greenwich",0],
                 UNIT["degree",0.0174532925199433],
                 AUTHORITY["EPSG","4326"]],
             PROJECTION["Mercator_1SP"],
             PARAMETER["central_meridian",0],
             PARAMETER["scale_factor",1],
             PARAMETER["false_easting",0],
             PARAMETER["false_northing",0],
             UNIT["metre",1,
                 AUTHORITY["EPSG","9001"]]]
    """

    def __init__(self):
        "Initialize the TMS Global Mercator pyramid"
        self.tileSize = SCENE_MAP_TILE_SIZE
        self.zoomLevel = SCENE_DEFAULT_ZOOM
        self.initialResolution = 2 * math.pi * EQUATOR_RADIUS_METERS / self.tileSize
        # 156543.03392804062 for tileSize 256 pixels
        self.originShift = 2 * math.pi * EQUATOR_RADIUS_METERS / 2.0
        # 20037508.342789244

    # Meters is a projection-method, not a measurement unit...
    # it is an xy grid based on meters.
    def LatLonToMeters(self, lat, lon):
        "Converts given lat/lon in WGS84 Datum to XY in Spherical Mercator EPSG:900913"
        mx = lon * self.originShift / 180.0
        my = math.log(math.tan((90 + lat) * math.pi / 360.0)) / (math.pi / 180.0)

        my = my * self.originShift / 180.0
        return mx, my

    def MetersToLatLon(self, mx, my):
        "Converts XY point from Spherical Mercator EPSG:900913 to lat/lon in WGS84 Datum"

        lon = (mx / self.originShift) * 180.0
        lat = (my / self.originShift) * 180.0

        lat = 180 / math.pi * (2 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
        return lat, lon

    def PixelsToMeters(self, px, py, zoom=None):
        "Converts pixel coordinates in given zoom level of pyramid to EPSG:900913"
        if zoom is None:
            zoom = self.zoomLevel
        res = self.Resolution(zoom)
        mx = px * res - self.originShift
        my = py * res - self.originShift
        return mx, my

    def MetersToPixels(self, mx, my, zoom=None):
        "Converts EPSG:900913 to pyramid pixel coordinates in given zoom level"
        if zoom is None:
            zoom = self.zoomLevel
        res = self.Resolution(zoom)
        px = (mx + self.originShift) / res
        py = (my + self.originShift) / res
        return px, py

    def PixelsToTile(self, px, py):
        "Returns a tile covering region in given pixel coordinates"

        tx = int(math.ceil(px / float(self.tileSize)) - 1)
        ty = int(math.ceil(py / float(self.tileSize)) - 1)
        return tx, ty

    def PixelsToRaster(self, px, py, zoom=None):
        "Move the origin of pixel coordinates to top-left corner"
        if zoom is None:
            zoom = self.zoomLevel
        mapSize = self.tileSize << zoom
        return px, mapSize - py

    def MetersToTile(self, mx, my, zoom=None):
        "Returns tile for given mercator coordinates"
        if zoom is None:
            zoom = self.zoomLevel
        px, py = self.MetersToPixels(mx, my, zoom)
        return self.PixelsToTile(px, py)

    def TileBounds(self, tx, ty, zoom=None):
        "Returns bounds of the given tile in EPSG:900913 coordinates"
        if zoom is None:
            zoom = self.zoomLevel
        minx, miny = self.PixelsToMeters(tx * self.tileSize, ty * self.tileSize, zoom)
        maxx, maxy = self.PixelsToMeters((tx + 1) * self.tileSize, (ty + 1) * self.tileSize, zoom)
        return (minx, miny, maxx, maxy)

    def TileLatLonBounds(self, tx, ty, zoom=None):
        "Returns bounds of the given tile in latutude/longitude using WGS84 datum"
        if zoom is None:
            zoom = self.zoomLevel
        bounds = self.TileBounds(tx, ty, zoom)
        minLat, minLon = self.MetersToLatLon(bounds[0], bounds[1])
        maxLat, maxLon = self.MetersToLatLon(bounds[2], bounds[3])

        return (minLat, minLon, maxLat, maxLon)

    def Resolution(self, zoom=None):
        "Resolution (meters/pixel) for given zoom level (measured at Equator)"
        if zoom is None:
            zoom = self.zoomLevel
        return (2 * math.pi * 6378137) / (self.tileSize * 2**zoom)
        return self.initialResolution / (2 ** zoom)

    def ZoomForPixelSize(self, pixelSize):
        "Maximal scaledown zoom of the pyramid closest to the pixelSize."

        for i in range(30):
            if pixelSize > self.Resolution(i):
                return i - 1 if i != 0 else 0  # We don't want to scale up

    def GoogleTile(self, tx, ty, zoom=None):
        "Converts TMS tile coordinates to Google Tile coordinates"
        if zoom is None:
            zoom = self.zoomLevel
        # coordinate origin is moved from bottom-left to top-left corner of the extent
        return tx, (2 ** zoom - 1) - ty

    def QuadTree(self, tx, ty, zoom=None):
        "Converts TMS tile coordinates to Microsoft QuadTree"
        if zoom is None:
            zoom = self.zoomLevel
        quadKey = ""
        ty = (2 ** zoom - 1) - ty
        for i in range(zoom, 0, -1):
            digit = 0
            mask = 1 << (i - 1)
            if (tx & mask) != 0:
                digit += 1
            if (ty & mask) != 0:
                digit += 2
            quadKey += str(digit)

        return quadKey

# import math
# from enum import Enum
#
# from PySide6.QtCore import QPointF
# from haversine import haversine, Unit  # we should remove this package.
#
#
# # EQUATOR_LENGTH_METERS = 40075004
# # EQUATOR_RADIUS_METERS = 6378137.0
# # POLAR_RADIUS_METERS = 6356752.3
# # The International Union of Geodesy and Geophysics (IUGG) defines the mean radius (denoted R1) to be
# from Config.Constants import SCENE_DEFAULT_ZOOM, DEGREES_NE
#
# WORLD_MEAN_RADIUS_METERS = 6371008.8
#
#
# class DistanceUnit(Enum):
#     KILOMETERS = 'km'
#     METERS = 'm'
#     MILES = 'mi'
#     NAUTICAL_MILES = 'nmi'
#     FEET = 'ft'
#     INCHES = 'in'
#
#     # Unit values taken from http://www.unitconversion.org/unit_converter/length.html
#     _CONVERSIONS = {
#             'km': 1.0,
#             'm': 1000.0,
#             'mi': 0.621371192,
#             'nmi': 0.539956803,
#             'ft': 3280.839895013,
#             'in': 39370.078740158
#         }
#
#     @classmethod
#     def convert(cls, from_value: float, from_unit, to_unit):
#         f = cls._CONVERSIONS[from_unit]
#         t = cls._CONVERSIONS[to_unit]
#         f_value = from_value / f # value in km
#         return (f_value * t)
#
#
# class TranslateCoordinates:
#
#     """
#         lat_lng = latitude/longitude, WGS84 coordinate, EPSG:4326
#         xy = EPSG:900913, references to both scene coordinate as google world-coordinate (Spherical Mercator map projection coordinates (google & bing?)  EPSG.io
#         p_xy = The coordinate of a pixel within the ViewPort (and not scene!), we should try to avoid this.
#
#         check: https://www.maptiler.com/google-maps-coordinates-tile-bounds-projection/
#
#
#         world coordinates are the same as pixel-coordinates at zoom level 0.
#         Yet they are of type FLOAT so you can have a coordinate far more specific then a pixel on a 256x256 sized world map.
#         As the world map is 256x256, the world coordinates can not be greater then 256x256. Map precision is accomplished by the float value.
#     """
#
#
#     def latlng_at_distance(self, from_latlng: QPointF, distance_in_meters: float, heading_degrees: float) -> QPointF:
#             """
#             This is the code used by google map (SphericalUtil.java)
#             https://stackoverflow.com/questions/8586635/convert-meters-to-latitude-longitude-from-any-point
#             Whenever the API needs to translate a location in the world to a location on a map, it first translates latitude and longitude values into a world coordinate.
#             The API uses the Mercator projection to perform this translation.
#             Latitude and longitude values, which reference a point on the world uniquely. (Google uses the World Geodetic System WGS84 standard.)
#
#             :param location_start:
#             :param length:
#             :param azimuth:
#             :return:
#             """
#             distance = distance_in_meters / WORLD_MEAN_RADIUS_METERS
#             heading = math.radians(heading_degrees)
#             from_latitude = math.radians(from_latlng.x())
#             from_longitude = math.radians(from_latlng.y())
#             cos_distance = math.cos(distance)
#             sin_distance = math.sin(distance)
#             sin_from_latitude = math.sin(from_latitude)
#             cos_from_latitude = math.cos(from_latitude)
#             sin_latitude = cos_distance * sin_from_latitude + sin_distance * cos_from_latitude * math.cos(heading)
#             distance_longitude = math.atan2(sin_distance * cos_from_latitude * math.sin(heading),
#                                             cos_distance - sin_from_latitude * sin_latitude)
#             latitude = math.degrees(math.asin(sin_latitude))
#             longitude = math.degrees(from_longitude + distance_longitude)
#             return QPointF(latitude, longitude)
#
#     def xy_2_latlng(self, xy: QPointF) -> QPointF:
#         """
#             convert Google-style Mercator tile coordinate to (lat, lng)
#             @see https://github.com/hrldcpr/mercator.py
#         """
#         x = xy.x()
#         y = xy.y()
#
#         lat_rad = math.pi - 2 * math.pi * y / math.pow(2, SCENE_DEFAULT_ZOOM)
#         lat_rad = 2 * math.atan(math.exp(lat_rad)) - math.pi / 2
#         lat = math.degrees(lat_rad)
#
#         lng = -180.0 + 360.0 * x / math.pow(2, SCENE_DEFAULT_ZOOM)
#
#         ret = QPointF(lat, lng)
#         # ret.setX(lat)
#         # ret.setY(lng)
#         return ret
#
#     def latlng_2_xy(self, latlng: QPointF) -> QPointF:
#         lat = latlng.x()
#         lng = latlng.y()
#
#         siny = math.sin((lat * math.pi) / 180);
#         # Truncating to 0.9999 effectively limits latitude to 89.189. This is
#         # about a third of a tile past the edge of the world tile.
#         siny = min(max(siny, -0.9999), 0.9999);
#
#         y = 256 * (0.5 + lng / 360)
#         x = 256 * (0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi))
#         return QPointF(y, x)
#
#     def latlng_2_mercator(self, latlng: QPointF) -> QPointF:
#         """
#             convert lat/lng to Google-style Mercator tile coordinate (x, y)
#             @see https://github.com/hrldcpr/mercator.py
#         """
#         lat = latlng.x()
#         lng = latlng.y()
#
#
#         lat_rad = math.radians(lat)
#         lat_rad = math.log(math.tan((lat_rad + math.pi / 2) / 2))
#
#         x = math.pow(2, SCENE_DEFAULT_ZOOM) * (lng + 180.0) / 360.0
#         y = math.pow(2, SCENE_DEFAULT_ZOOM) * (math.pi - lat_rad) / (2 * math.pi)
#         ret = QPointF(x, y)
#         return ret
#
#     "Caching dict"
#     _cache_xy_per_km_at = {}
#
#     def xy_per_km_at(self, latlng: QPointF) -> float:
#         """
#             Returns the amount of xy points per kilometer.
#             The lat-lng is required to take into account the Mercator projection.
#
#         """
#         cache_key = f'lat_{latlng.x()}-lng_{latlng.y()}'
#         try:
#             return self._cache_xy_per_km_at[cache_key]
#         except KeyError:
#             xy = self.latlng_2_xy(latlng)
#             # @todo is DEGREES_NE the best to chose?
#             to_latlng = self.latlng_at_distance(latlng, 1000, DEGREES_NE)
#             to_xy = self.latlng_2_xy(to_latlng)
#
#             diff = to_xy - xy
#             self._cache_xy_per_km_at[cache_key] = diff.x() + diff.y()
#         return self._cache_xy_per_km_at[cache_key]
#
# #
# # class CalcDistance:
# #     """
# #         We have the following grid units
# #             - lat/long
# #             - google_maps xy    "World Geodetic System WGS84"
# #             - pixel xy at zoom-level
# #             - scene xy  "World Geodetic System WGS84"
# #             - view xy
# #     """
# #
# #     def __init__(self, lat_lng: QPointF, zoom_level: float):
# #         self.lat_lng = lat_lng
# #         self.zoom_level = zoom_level
# #
# #     def between_latlng(self, from_lat_lng: QPointF, to_lat_lng: QPointF = None, unit: DistanceUnit=DistanceUnit.METERS) -> float:
# #         if to_lat_lng is None:
# #             to_lat_lng = self.lat_lng
# #
# #         return self._haversine(from_lat_lng, to_lat_lng, unit)
# #
# #     def between_xy(self, from_xy: QPointF, to_xy: QPointF = None, unit=DistanceUnit.METERS) -> float:
# #         pass
# #
# #     def xy_2_latlng(self, xy: QPointF) -> QPointF:
# #         """
# #             convert Google-style Mercator tile coordinate to (lat, lng)
# #             @see https://github.com/hrldcpr/mercator.py
# #         """
# #         x = xy.x()
# #         y = xy.y()
# #
# #         lat_rad = math.pi - 2 * math.pi * y / math.pow(2, self.zoom_level)
# #         lat_rad = 2 * math.atan(math.exp(lat_rad)) - math.pi / 2
# #         lat = math.degrees(lat_rad)
# #
# #         lng = -180.0 + 360.0 * x / math.pow(2, self.zoom_level)
# #
# #         ret = QPointF()
# #         ret.setX(lat)
# #         ret.setY(lng)
# #         return ret
# #
# #     def _haversine(self, from_latlng: QPointF, to_latlng: QPointF, unit: DistanceUnit) -> float:
# #         """ Calculate the great-circle distance between two points on the Earth surface.
# #
# #         Takes two 2-tuples, containing the latitude and longitude of each point in decimal degrees,
# #         and, optionally, a unit of length.
# #
# #         :param point1: first point; tuple of (latitude, longitude) in decimal degrees
# #         :param point2: second point; tuple of (latitude, longitude) in decimal degrees
# #         :param unit: a member of haversine.Unit, or, equivalently, a string containing the
# #                      initials of its corresponding unit of measurement (i.e. miles = mi)
# #                      default 'km' (kilometers).
# #
# #         Example: ``haversine((45.7597, 4.8422), (48.8567, 2.3508), unit=Unit.METERS)``
# #
# #         Precondition: ``unit`` is a supported unit (supported units are listed in the `Unit` enum)
# #
# #         :return: the distance between the two points in the requested unit, as a float.
# #
# #         The default returned unit is kilometers. The default unit can be changed by
# #         setting the unit parameter to a member of ``haversine.Unit``
# #         (e.g. ``haversine.Unit.INCHES``), or, equivalently, to a string containing the
# #         corresponding abbreviation (e.g. 'in'). All available units can be found in the ``Unit`` enum.
# #         """
# #
# #         # unpack latitude/longitude
# #         lat1, lng1 = from_latlng.toTuple()
# #         lat2, lng2 = to_latlng.toTuple()
# #
# #         # convert all latitudes/longitudes from decimal degrees to radians
# #         lat1 = math.radians(lat1)
# #         lng1 = math.radians(lng1)
# #         lat2 = math.radians(lat2)
# #         lng2 = math.radians(lng2)
# #
# #         # calculate haversine
# #         lat = lat2 - lat1
# #         lng = lng2 - lng1
# #         d = math.sin(lat * 0.5) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lng * 0.5) ** 2
# #
# #         return 2 * DistanceUnit.convert(MEAN_RADIUS_METERS, DistanceUnit.METERS, unit) * math.asin(math.sqrt(d))
