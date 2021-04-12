import logging
import math

from PySide6.QtCore import QPointF, QSize, QThreadPool

from Config.Constants import GOOGLE_STATIC_MAPS_URL, GOOGLE_STATIC_MAPS_API_KEY, GOOGLE_MAPS_SCALING
from Gui.Scene.Providers.Mixins import TileGridMixin
from Models.TableModels import SqlManager
from Utils.Settings import Preferences


class GoogleMapsProvider(TileGridMixin):

    TILE_HEIGHT = 640
    TILE_WIDTH = 640

    MAP_TYPE = 'satellite'
    IMAGE_EXTENSION = 'jpg'

    def parent(self):
        return self._parent

    def __init__(self, parent):
        self._parent = parent
        self.log = logging.getLogger(__name__)
        self.sql_manager = SqlManager()
        self.thread_pool = QThreadPool()

        self.map_center_latlng: QPointF = None
        self.map_zoom: float = self.parent().zoom_level
        self.window_size: QSize = None
        # when moving, map_center is different from window_center by QPointF.x() & QPointF.y()
        self.window_offset: QPointF = QPointF(0.0, 0.0)


    def render(self):
        self.log.debug("GoogleMapsProvider Render called")
        if self.parent().map_center != self.map_center_latlng:
            self.map_center_latlng = self.parent().map_center
            self.map_zoom = self.parent().zoom_level
            self.window_size = self.parent().viewport_size
            # @todo screen move needs window offset to be re-set...
            self._render_full()

    def _render_full(self):
        """
            We will do a complete re-render of the scene.
            All tiles will be removed and re-rendered.

        :return:
        """
        self.log.info("GoogleMapsProvider Full re-render")
        tiles = self.get_tiles_for_grid(
            map_center=self.map_center_latlng,
            window_width=self.window_size.width(),
            window_height=self.window_size.height(),
            window_offset=self.window_offset,
            tile_width=self.TILE_WIDTH,
            tile_height=self.TILE_HEIGHT,
            zoom_level=self.map_zoom
        )

        for tile in tiles:
            self.parent().addToGroup(tile.graphics_item)
            worker = tile.thread_object()
            worker.set_url(self)
            self.thread_pool.start(worker)

    def _flush(self):
        children = self.parent().childItems()
        if len(children) > 0:
            for item in children:
                self.parent().removeItem(item)  # @todo I might actually have to remove the item from the map_view instead...?

    def get_tile_url(self, lat_lng: QPointF, zoom_level: int):
        return f'{GOOGLE_STATIC_MAPS_URL}' \
               f'?key={GOOGLE_STATIC_MAPS_API_KEY}' \
               f'&center={lat_lng.x()},{lat_lng.y()}' \
               f'&scaling={Preferences.get("google_maps_scaling", GOOGLE_MAPS_SCALING, int)}' \
               f'&zoom={math.floor(zoom_level)}' \
               f'&maptype={self.MAP_TYPE}' \
               f'&size={self.TILE_WIDTH}x{self.TILE_HEIGHT}' \
               f'&format={self.IMAGE_EXTENSION}'

    def get_tile_cache_name(self, lat_lng: QPointF, zoom_level: int):
        return f'gsm_zoom-{math.floor(zoom_level)}_lat-{lat_lng.x()}_lng-{lat_lng.y()}'
