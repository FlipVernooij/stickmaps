import logging

from PySide6.QtCore import QObject, Signal, Qt, QPointF, QPoint, QRunnable, Slot, QSize
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem, QGraphicsTextItem

from Utils import Request


class GridTileObject(QObject):

    _pixmap_placeholder = None

    s_pixmap_ready = Signal(QPixmap, object)

    @property
    def pixmap_placeholder(self):
        if self._pixmap_placeholder is None:
            self._pixmap_placeholder = QPixmap(self.tile_size.width(), self.tile_size.height())
            self._pixmap_placeholder.fill(Qt.red)
        return self._pixmap_placeholder

    def __init__(self, lat_lng: QPointF, tile_xy: QPoint, tile_size: QSize, zoom_level: float):
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.tile_xy = tile_xy
        self.lat_lng = lat_lng
        self.tile_size = tile_size
        self.zoom_level = zoom_level

        self.graphics_item = QGraphicsPixmapItem()
        self.s_pixmap_ready.connect(self.update_pixmap)

        self.type = 'default'

    def __repr__(self):
        return f'{self.type} x:{self.tile_xy.x()} / y:{self.tile_xy.y()}  - {self.lat()} / {self.lng()}'

    def __eq__(self, other) -> bool:
        if self.x() != other.x():
            return False
        if self.y() != other.y():
            return False
        if self.lat_lng != other.lat_lng:
            return False
        if self.zoom_level != other.zoom_level:
            return False
        return True

    def x(self):
        return self.tile_xy.x()

    def y(self):
        return self.tile_xy.y()

    def lat(self):
        return self.lat_lng.x()

    def lng(self):
        return self.lat_lng.y()

    def x_pos(self):
        # -1 as we need the start of the tile, not the end
        return (self.x()-1) * self.tile_size.width()

    def y_pos(self):
        # -1 as we need the start of the tile, not the end
        return (self.y()-1) * self.tile_size.height()

    def is_within_grid(self, grid_width_num: int, grid_height_num: int) -> bool:
        if self.x() > grid_width_num or self.x() < 1:
            return False
        if self.y() > grid_height_num or self.y() < 1:
            return False
        return True


    def thread_object(self):
        self.graphics_item.setX(self.x_pos())
        self.graphics_item.setY(self.y_pos())
        self.graphics_item.setPixmap(self.pixmap_placeholder)
        obj = GridTileWorkerObject(self)

        return obj

    @Slot(QPixmap, object)
    def update_pixmap(self, pixmap: QPixmap, grid_tile_object: object):
        grid_tile_object.graphics_item.setPixmap(pixmap)


class GridTileWorkerObject(QRunnable):

    def __init__(self, tile: GridTileObject):
        super().__init__()
        self.log = logging.getLogger(__name__)
        self.tile = tile
        self.url = None
        self.cache_file = None

    def set_url(self, provider):
        self.url = provider.get_tile_url(self.tile.lat_lng, self.tile.zoom_level)
        self.cache_file = provider.get_tile_cache_name(self.tile.lat_lng, self.tile.zoom_level)

    def run(self):
        file = Request.cached_image(self.url, self.cache_file)
        # @todo I can probably do without the scaling...?
        pixmap = QPixmap.fromImage(file).scaled(self.tile.tile_size.width(), self.tile.tile_size.height(), Qt.KeepAspectRatioByExpanding)
        self.tile.s_pixmap_ready.emit(pixmap, self.tile)
