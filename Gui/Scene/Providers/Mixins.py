import math
import pyIGRF
from PySide6.QtCore import QPointF, QPoint, QSize

from Gui.Scene.Providers.DataObject import GridTileObject


class GeoMixin:
    WORLD_TILE_SIZE = 256

    HEADING_NORTH = 360
    HEADING_NORTH_EAST = 45
    HEADING_EAST = 90
    HEADING_SOUTH_EAST = 135
    HEADING_SOUTH = 180
    HEADING_SOUTH_WEST = 225
    HEADING_WEST = 270
    HEADING_NORTH_WEST = 315

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

    def latlng_2_xy(self, latlng: QPointF, zoom: int) -> QPointF:
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

    """ @todo UNTESTED, CHECK THIS!!"""
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

class TileGridMixin(GeoMixin):

    def get_tiles_for_grid(self,
                           map_center: QPointF,
                           window_width: int,
                           window_height: int,
                           window_offset: QPointF,
                           tile_width: int,
                           tile_height: int,
                           zoom_level: float

                           ) -> list:
        """
            This method returns a list with all the lat/lng & x/y info for every tile that needs to be rendered.
            It will render 1 extra row on each side as a scroll-buffer as an attempt to allow fluid scrolling/zooming.

            As a extra gadget the order of the elements in the list should show a cool pattern when loading the images.

        :param window_width: int
        :param window_height: int
        :return: list
        """

        if window_offset != QPointF(0.0, 0.0):
            self.log.error("Window offset found but not implemented.")
        if round(zoom_level) != zoom_level:
            self.log.error('Floating zoom level found but not implemented.')

        tile_count_width = math.ceil(window_width / tile_width) + 2
        tile_count_height = math.ceil(window_height / tile_height) + 2

        if tile_count_width % 2 == 0:
            tile_count_width += 1
        if tile_count_height % 2 == 0:
            tile_count_height += 1

        tile_size = QSize(tile_width, tile_height)

        self.log.info(f'Grid-size set to w/h {tile_count_width}/{tile_count_height}')

        center_tile = GridTileObject(
            lat_lng=map_center,
            tile_xy=QPoint(math.ceil(tile_count_width / 2), math.ceil(tile_count_height / 2)),
            tile_size=tile_size,
            zoom_level=zoom_level
        )
        render_tiles = [center_tile]
        c_ne = center_tile
        c_se = center_tile
        c_sw = center_tile
        c_nw = center_tile
        while True:
            end_corner_loop = 0
            c_ne = self.next_tile(c_ne, self.HEADING_NORTH_EAST, tile_size, zoom_level)
            c_se = self.next_tile(c_se, self.HEADING_SOUTH_EAST, tile_size, zoom_level)
            c_sw = self.next_tile(c_sw, self.HEADING_SOUTH_WEST, tile_size, zoom_level)
            c_nw = self.next_tile(c_nw, self.HEADING_NORTH_WEST, tile_size, zoom_level)

            if c_ne.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position (widescreen)
                if c_ne.x() <= tile_count_width:
                    c_ne = self.next_tile(c_ne, self.HEADING_SOUTH, tile_size, zoom_level)
                    render_tiles.append(c_ne)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_ne)

            if c_se.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position  (widscreen)
                if c_se.y() <= tile_count_height:
                    c_se = self.next_tile(c_se, self.HEADING_WEST, tile_size, zoom_level)
                    render_tiles.append(c_se)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_se)

            if c_sw.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position (widscreen)
                if c_sw.x() >= 1:
                    c_sw = self.next_tile(c_sw, self.HEADING_NORTH, tile_size, zoom_level)
                    render_tiles.append(c_sw)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_sw)

            if c_nw.is_within_grid(tile_count_width, tile_count_height) is False:
                if c_nw.y() >= 1:
                    c_nw = self.next_tile(c_nw, self.HEADING_EAST, tile_size, zoom_level)
                    render_tiles.append(c_nw)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_nw)

            r_s = c_ne
            r_w = c_se
            r_n = c_sw
            r_e = c_nw

            while True:
                end_row_loop = 0
                r_s = self.next_tile(r_s, self.HEADING_SOUTH, tile_size, zoom_level)
                if r_s.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_s)

                r_w = self.next_tile(r_w, self.HEADING_WEST, tile_size, zoom_level)
                if r_w.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_w)

                r_n = self.next_tile(r_n, self.HEADING_NORTH, tile_size, zoom_level)
                if r_n.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_n)

                r_e = self.next_tile(r_e, self.HEADING_EAST, tile_size, zoom_level)
                if r_e.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_e)

                if end_row_loop == 4:
                    break

            if end_corner_loop == 4:
                break

        return render_tiles

    def next_tile(self, last_corner: GridTileObject, heading: int, tile_size: QSize, zoom_level: float):
        rounded_zoom_level = math.floor(zoom_level)
        latlng = self.latlng_2_xy(last_corner.lat_lng, rounded_zoom_level)
        offset = QPoint(0, 0)

        map_height = self.xy_value_for_pixels(tile_size.height())
        map_width = self.xy_value_for_pixels(tile_size.width())

        if heading in (self.HEADING_NORTH, self.HEADING_NORTH_EAST, self.HEADING_NORTH_WEST):
            latlng.setY(latlng.y() + (map_height * -1))
            offset.setY(1 * -1)
        if heading in (self.HEADING_SOUTH, self.HEADING_SOUTH_EAST, self.HEADING_SOUTH_WEST):
            latlng.setY(latlng.y() + map_height)
            offset.setY(1)
        if heading in (self.HEADING_EAST, self.HEADING_NORTH_EAST, self.HEADING_SOUTH_EAST):
            latlng.setX(latlng.x() + map_width)
            offset.setX(1)
        if heading in (self.HEADING_WEST, self.HEADING_NORTH_WEST, self.HEADING_SOUTH_WEST):
            latlng.setX(latlng.x() + (map_width * -1))
            offset.setX(1 * -1)

        lat_lng = self.xy_2_latlng(latlng, rounded_zoom_level)
        tile_xy = last_corner.tile_xy + offset

        return GridTileObject(
            lat_lng=lat_lng,
            tile_xy=tile_xy,
            tile_size=tile_size,
            zoom_level=zoom_level
        )
