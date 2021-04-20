import logging
import math

from PySide6.QtCore import QPointF, QSize

from Config.Constants import GOOGLE_STATIC_MAPS_URL, GOOGLE_STATIC_MAPS_API_KEY, GOOGLE_MAPS_SCALING
from Gui.Scene.Providers.Mixins import TileGridMixin
from Utils.Settings import Preferences


class GoogleMapsProvider(TileGridMixin):

    TILE_SIZE = QSize(640, 640)
    MAP_TYPE = 'satellite'
    IMAGE_EXTENSION = 'jpg'

    def __init__(self, parent):
        self._parent = parent
        self.log = logging.getLogger(__name__)

    def get_tile_url(self, lat_lng: QPointF, zoom_level: int):
        return f'{GOOGLE_STATIC_MAPS_URL}' \
               f'?key={GOOGLE_STATIC_MAPS_API_KEY}' \
               f'&center={lat_lng.x()},{lat_lng.y()}' \
               f'&scaling={Preferences.get("google_maps_scaling", GOOGLE_MAPS_SCALING, int)}' \
               f'&zoom={math.floor(zoom_level)}' \
               f'&maptype={self.MAP_TYPE}' \
               f'&size={self.TILE_SIZE.width()}x{self.TILE_SIZE.height()}' \
               f'&format={self.IMAGE_EXTENSION}'

    def get_tile_cache_name(self, lat_lng: QPointF, zoom_level: int):
        return f'gsm_zoom-{math.floor(zoom_level)}_lat-{lat_lng.x()}_lng-{lat_lng.y()}.{self.IMAGE_EXTENSION}'
