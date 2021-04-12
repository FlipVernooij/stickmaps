import datetime
import logging
import pathlib
import shutil
from time import sleep

import pyIGRF
import requests
from PySide6.QtCore import QPointF, Qt, QPoint, QRunnable, QThreadPool, Signal, QObject
import math

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsItemGroup

from Config.Constants import GOOGLE_STATIC_MAPS_URL, GOOGLE_STATIC_MAPS_API_KEY, GOOGLE_MAPS_SCALING, \
    APPLICATION_CACHE_DIR, DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from Models.TableModels import ProjectSettings, SqlManager
from Utils.Settings import Preferences




class TileWorkerObject(QRunnable, FileFetchMixin):

    def __init__(self, tile):
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.tile = tile
        # self.graphic_object = QGraphicsPixmapItem()
        # self.graphic_object.setY(tile.y_pos())
        # self.graphic_object.setX(tile.x_pos())
        #
        # pixmap = QPixmap(tile.TILE_WIDTH, tile.TILE_HEIGHT)
        # pixmap.fill(Qt.red)
        # self.graphic_object.setPixmap(pixmap)
        #
        # self.s_set_pixmap.connect(self.set_pixmap)


    def run(self):
        file = self._request_image(self.tile.lat_lng, self.tile.ZOOM)

        pixmap = QPixmap.fromImage(file).scaled(self.tile.TILE_WIDTH, self.tile.TILE_HEIGHT, Qt.KeepAspectRatioByExpanding)
        self.tile.s_pixmap_ready.emit(pixmap)


class TileObject(QObject):

    TILE_WIDTH = 640
    TILE_HEIGHT = 640
    ZOOM = 20

    _pixmap_placeholder = None

    s_pixmap_ready = Signal(QPixmap)

    @property
    def pixmap_placeholder(self):
        if self._pixmap_placeholder is None:
            self._pixmap_placeholder = QPixmap(self.TILE_WIDTH, self.TILE_HEIGHT)
            self._pixmap_placeholder.fill(Qt.gray)
        return self._pixmap_placeholder

    def __init__(self, lat_lng: QPointF, tile_xy: QPoint):
        super().__init__()
        self.tile_xy = tile_xy
        self.lat_lng = lat_lng

        self.graphics_item = QGraphicsPixmapItem()

    def __repr__(self):
        return f'x:{self.tile_xy.x()} / y:{self.tile_xy.y()}  - {self.lat()} / {self.lng()}'

    def x(self):
        return self.tile_xy.x()

    def y(self):
        return self.tile_xy.y()

    def lat(self):
        return self.lat_lng.x()

    def lng(self):
        return self.lat_lng.y()

    def x_pos(self):
        return self.x() * self.TILE_WIDTH

    def y_pos(self):
        return self.y() * self.TILE_HEIGHT

    def is_within_grid(self, grid_width: int, grid_height) -> bool:
        if self.x() > grid_width or self.x() < 1:
            return False
        if self.y() > grid_height or self.y() < 1:
            return False
        return True

    def thread_object(self):
        self.graphics_item.setX(self.x_pos())
        self.graphics_item.setY(self.y_pos())
        self.graphics_item.setPixmap(self.pixmap_placeholder)
        obj = TileWorkerObject(self)
        self.s_pixmap_ready.connect(self.update_pixmap)
        return obj

    def update_pixmap(self, pixmap):
        self.graphics_item.setPixmap(pixmap)

class OverlayGoogleMaps(GeoMixin, FileFetchMixin):

    HEADING_NORTH = 360
    HEADING_NORTH_EAST = 45
    HEADING_EAST = 90
    HEADING_SOUTH_EAST = 135
    HEADING_SOUTH = 180
    HEADING_SOUTH_WEST = 225
    HEADING_WEST = 270
    HEADING_NORTH_WEST = 315


    def __init__(self, parent, map_group: QGraphicsItemGroup):
        self.parent = parent
        self.thead_pool = QThreadPool()
        self.log = logging.getLogger(__name__)
        self.sql_manager = SqlManager()
        self.zoom = 20
        self._tile_height = 640
        self._tile_width = 640

        self.project = self.sql_manager.factor(ProjectSettings).get()
        self.viewport_size = self.parent.parent().viewport().size()
        self.map_group = map_group

        self.map_is_shown = False

    @property
    def tile_height(self):
        """
            I am dividing the tile size as I am requesting a 2X, yet displaying it as such shows a pretty low res image.
            @todo, figure this out and remove these properties.. and use the actual properties again.
        """
        return self._tile_height

    @property
    def tile_width(self):
        return self._tile_width

    def reload(self):
        self.project = self.sql_manager.factor(ProjectSettings).get()
        self.viewport_size = self.parent.parent().viewport().size()
        children = self.map_group.childItems()
        if len(children) > 0:
            for item in self.map_group.childItems():
                self.parent.removeItem(item)
        if self.map_is_shown is False:
            self.render()

        self.map_is_shown = not self.map_is_shown

    def render(self):
        self.tiles = self.get_tiles_for_grid(self.viewport_size.width(), self.viewport_size.height())

        for tile in self.tiles:
            self.map_group.addToGroup(tile.graphics_item)
            worker = tile.thread_object()
            self.thead_pool.start(worker)

    def get_tiles_for_grid(self, screen_width: int, screen_height: int) -> list:
        """
            This method returns a list with all the lat/lng & x/y info for every tile that needs to be rendered.
            It will render 1 extra row on each side as a scroll-buffer as an attempt to allow fluid scrolling/zooming.

            As a extra gadget the order of the elements in the list should show a cool pattern when loading the images.

        :param screen_width: int
        :param screen_height: int
        :return: list
        """
        tile_count_width = math.ceil(screen_width / self.tile_width) + 2
        tile_count_height = math.ceil(screen_height / self.tile_height) + 2


        if tile_count_width % 2 == 0:
            tile_count_width += 1
        if tile_count_height % 2 == 0:
            tile_count_height += 1

        self.log.info(f'Grid-size set to w/h {tile_count_width}/{tile_count_height}')

        center_tile = TileObject(
            lat_lng=QPointF(DEFAULT_LATITUDE, DEFAULT_LONGITUDE),
            tile_xy=QPoint(math.ceil(tile_count_width/ 2), math.ceil(tile_count_height / 2))
        )
        render_tiles = [center_tile]
        c_ne = center_tile
        c_se = center_tile
        c_sw = center_tile
        c_nw = center_tile
        while True:
            end_corner_loop = 0
            c_ne = self.next_tile(c_ne, self.HEADING_NORTH_EAST)
            c_se = self.next_tile(c_se, self.HEADING_SOUTH_EAST)
            c_sw = self.next_tile(c_sw, self.HEADING_SOUTH_WEST)
            c_nw = self.next_tile(c_nw, self.HEADING_NORTH_WEST)

            if c_ne.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position (widscreen)
                if c_ne.x() <= tile_count_width:
                    c_ne = self.next_tile(c_ne, self.HEADING_SOUTH)
                    render_tiles.append(c_ne)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_ne)

            if c_se.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position  (widscreen)
                if c_se.y() <= tile_count_height:
                    c_se = self.next_tile(c_se, self.HEADING_WEST)
                    render_tiles.append(c_se)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_se)

            if c_sw.is_within_grid(tile_count_width, tile_count_height) is False:
                # check if we need to change corner position (widscreen)
                if c_sw.x() >= 1:
                    c_sw = self.next_tile(c_sw, self.HEADING_NORTH)
                    render_tiles.append(c_sw)
                else:
                    end_corner_loop += 1
            else:
                render_tiles.append(c_sw)

            if c_nw.is_within_grid(tile_count_width, tile_count_height) is False:
                if c_nw.y() >= 1:
                    c_nw = self.next_tile(c_nw, self.HEADING_EAST)
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
                r_s = self.next_tile(r_s, self.HEADING_SOUTH)
                if r_s.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_s)

                r_w = self.next_tile(r_w, self.HEADING_WEST)
                if r_w.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_w)

                r_n = self.next_tile(r_n, self.HEADING_NORTH)
                if r_n.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_n)

                r_e = self.next_tile(r_e, self.HEADING_EAST)
                if r_e.is_within_grid(tile_count_width, tile_count_height) is False:
                    end_row_loop += 1
                else:
                    render_tiles.append(r_e)

                if end_row_loop == 4:
                    break

            if end_corner_loop == 4:
                break
                
        return render_tiles
    
    def next_tile(self, last_corner: TileObject, heading: int):
        latlng = self.latlng_2_xy(last_corner.lat_lng, self.zoom)
        offset = QPoint(0, 0)

        map_height = self.xy_value_for_pixels(self._tile_height)
        map_width = self.xy_value_for_pixels(self._tile_width)

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

        lat_lng = self.xy_2_latlng(latlng, self.zoom)
        tile_xy = last_corner.tile_xy + offset

        return TileObject(lat_lng=lat_lng, tile_xy=tile_xy)
