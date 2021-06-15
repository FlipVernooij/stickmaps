import logging
import math

from PySide6.QtCore import QPointF, Slot, QSize, QRect, QPoint, QThreadPool, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsItemGroup, QGraphicsScene, QGraphicsItem

from Gui.Scene.Providers.DataObject import GridTileObject
from Gui.Scene.Providers.Mixins import TileGridMixin, GeoMixin
from Gui.Scene.Providers.Satellite import GoogleMapsProvider
from Models.TableModels import SqlManager



class GridOverlay(QGraphicsItem):

    def parent(self) -> QGraphicsScene:
        return self._parent

    def main_window(self):
        return self.parent().main_application

    def map_view(self):
        return self.parent().parent()

    def boundingRect(self):
        return self.scene_rect
    #
    # @Slot(dict)
    # def c_load_project(self, project: dict):
    #     self.update()
    #
    # @Slot(QRect, QRect)
    # def c_scene_resize(self, old_size: QRect, new_size: QRect):
    #     pass
    #     # self.update()

    @Slot(float, float)
    def c_zoom_changed(self, new_zoom: float, old_zoom: float):
        self.update()


    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        #self.setCacheMode(QGraphicsItem.ItemCoordinateCache)
        self.log = logging.getLogger(__name__)

        self.is_visible = True
        self.is_enabled = True

        self.scene_rect = self.parent().sceneRect()

        # self.main_window().s_load_project.connect(self.c_load_project)
        self.map_view().s_zoom_changed.connect(self.c_zoom_changed)


        # self.parent().parent().s_zoom_viewp.connect(self.c_zoom_viewport)

        # this will be multiplied by 10 when the grid gets to big
        # self.tile_size =  # 50 as meters in block 20.4


    def show(self):
        self.log.debug(f'Showing GridOverlay')
        self.is_visible = True
        self.setVisible(True)  # call on parent
        self.render()

    def hide(self):
        self.log.info(f'Hidding GridOverlay')
        self.is_visible = False
        self.setVisible(False)  # call on parent

    #def update(self):


    def paint(self, painter, option, widget, PySide6_QtWidgets_QWidget=None, NoneType=None, *args, **kwargs):
        if self.is_enabled is not True or self.is_visible is not True:
            self.log.debug("Grid overlay not visible")
            return
        self.log.debug('Grid overlay is rendered')

        self.scene_rect = self.parent().sceneRect()
        tile_size = self.get_grid_size(self.map_view().get_current_zoom())

        y_append = QPointF(0, tile_size)
        x_append = QPointF(tile_size, 0)

        view_rect = self.parent().view_rect()

        y_left = view_rect.topLeft()
        y_right = view_rect.topRight()
        x_top = view_rect.topLeft()
        x_bottom = view_rect.bottomLeft()
        painter.setPen(Qt.red)
        painter.drawRect(self.parent().sceneRect())
        painter.setPen(Qt.black)
        while True:
            break_loop = 0
            y_left += y_append
            y_right += y_append
            x_top += x_append
            x_bottom += x_append
            if y_left.y() > view_rect.bottomLeft().y():
                break_loop += 1
            else:
                painter.drawLine(y_left, y_right)
            if x_top.x() > view_rect.topRight().x():
                break_loop += 1
            else:
                painter.drawLine(x_top, x_bottom)
            if break_loop > 1:
                break

    def get_grid_size(self, zoom_level: float) -> int:
        return int(zoom_level)


class SatelliteOverlay(QGraphicsItemGroup, TileGridMixin, GeoMixin):

    def __init__(self, parent):
        self.render_count = 0
        super().__init__()
        self._parent = parent
        self.map_view = self.parent().parent()
        self.sql_manager = SqlManager()
        self.thread_pool = QThreadPool()
        self.log = logging.getLogger(__name__)
        self._provider = None

        # is the overlay enabled (do we have lat/lng?)
        self.is_enabled = False
        # is the overlay visible or hidden?
        self.is_visible = False

        # Size of the map-tiles as used in the grid (set by the provider)
        self.tile_size = QSize(0, 0)
        # the center of the map (the lat/lng set in the projectSettings)
        self.map_center_latlng = None
        # this is the center of the viewport as a xy, this is the same as map_center_latlng at project load, yet after moving or zooming this will be offset.
        self.view_center_xy = QPointF()

        self.viewport_size = QSize(0, 0) # I can not set this on __init__, this is done by the c_resize_viewport slot which is also called before displaying the application at boot.

        self.zoom_level = self.map_view.get_zoom()
        self.zoom_center = None  # zooming should occur at cursor,.. or map_center when done with slider or such


        # Signals
        self.map_view.s_project_changed.connect(self.c_project_changed)
        self.map_view.s_toggle_satellite.connect(self.c_toggle_visibility)

        self.map_view.s_resize_viewport.connect(self.c_resize_viewport)
        self.map_view.s_move_viewport.connect(self.c_move_viewport)
        self.map_view.s_zoom_viewport.connect(self.c_zoom_viewport)


        self.show()

    def boundingRect(self):
        return self.childrenBoundingRect()

    def parent(self):
        return self._parent

    def get_provider(self):
        if self._provider is None:
            self._provider = GoogleMapsProvider(self)
            self.tile_size = self._provider.TILE_SIZE
        return self._provider

    # Usablillaty methods

    def show(self):
        self.log.debug(f'Showing SatelliteOverlay')
        self.is_visible = True
        self.setVisible(True)  # call on parent
        self.render()

    def hide(self):
        self.log.info(f'Hidding SatelliteOverlay')
        self.is_visible = False
        self.setVisible(False)  # call on parent

    def center_on_view(self):
        view_rect = self.map_view.mapToScene(QRect(QPoint(0, 0), self.viewport_size)).boundingRect()

        sat_size = self.boundingRect()
        view_size = self.viewport_size

        left_offset = (sat_size.width() - view_size.width()) / 2
        top_offset = (sat_size.height() - view_size.height()) / 2

        self.setX(view_rect.left() - left_offset)
        self.setY(view_rect.top() - top_offset)


    def render(self):
        tile_colors = [
            #Qt.white,
            Qt.green,
            Qt.red,
            Qt.blue,
            Qt.yellow,
            Qt.black,
            Qt.gray
        ]

        if self.render_count >= len(tile_colors):
            self.render_count = 0

        pxmap = QPixmap(self.tile_size.width(), self.tile_size.height())
        pxmap.fill(tile_colors[self.render_count])
        self.log.debug(f'Setting color to: {tile_colors[self.render_count]} {self.render_count}')

        if self.is_enabled is not True or self.is_visible is not True:
            self.log.debug("Satellite overlay not visible")
            return

        grid = self._generate_grid()
        self.log.warning(f'Grid-Size: {grid["tile_count"]}, tile_count {len(grid["tiles"])}')
        self.flush()
        self.log.error(f'Bounding-box before: {self.boundingRect()}')
        for tile in grid['tiles']:
            worker = tile.thread_object()  # this sets the x/y.. ;p

            item = tile.graphics_item
            item.setPixmap(pxmap)

            self.addToGroup(item)
            #
            #worker.set_url(self.get_provider())
            #self.thread_pool.start(worker)

        self.center_on_view()
        self.log.error(f'Bounding-box after: {self.boundingRect()}')
        self.render_count += 1


    def flush(self):
        children = self.childItems()
        if len(children) > 0:
            for item in children:
                self.parent().removeItem(item)  # @todo I might actually have to remove the item from the map_view instead...?

        foo = 1

    def _set_center_latlng_for_xy(self, new_xy: QPointF):
        diff = self.view_center_xy - new_xy
        height_diff = self.xy_2_pixels(diff.y())
        width_diff = self.xy_2_pixels(diff.x())

        height_tiles = math.ceil(height_diff / self.tile_size.height())
        width_tiles = math.ceil(width_diff / self.tile_size.width())

        tile = GridTileObject(
            lat_lng=self.map_center_latlng,
            tile_xy=QPoint(0, 0),
            tile_size=self.tile_size,
            zoom_level=self.zoom_level
        )
        return self.get_latlng_for_tile(QPoint(width_tiles, height_tiles), tile)


    def _generate_grid(self):
        tiles = self.get_tiles_for_grid(
            map_center=self.map_center_latlng,  ## I should fix this
            window_width=self.viewport_size.width(),
            window_height=self.viewport_size.height(),
            tile_size=self.get_provider().TILE_SIZE,
            zoom_level=self.zoom_level
        )
        return tiles

    # Signals

    @Slot(dict)
    def c_project_changed(self, project: dict):
        """
            If anything in the projectSettings changed, this method is called.

        :param project:
        :return:
        """

        if project['latitude'] != '' and project['longitude'] != '':
            center = QPointF(project['latitude'], project['longitude'])
            if center != self.map_center_latlng:
                self.map_center_latlng = center
                # @todo This should not be LAT/LNG but a x/y position
                self.zoom_center = None  # when zooming without the mouse, we use the map center as the zoom center.
            self.is_enabled = True
            self.render()
        else:
            self.is_enabled = False

    @Slot(bool)
    def c_toggle_visibility(self, show: bool = None):
        if show is None:
            show = not self.is_visible
        if show is False:
            self.hide()
        else:
            self.show()

    @Slot(float, QPointF)
    def c_zoom_viewport(self, zoom: float, cursor_position: QPointF):
        self.log.info(f'Zooming SatelliteOverlay {zoom}')
        return
        self.zoom_level = zoom
        self.zoom_center = cursor_position
        self.render()

    @Slot(QSize)
    def c_resize_viewport(self, new_size: QSize):
        self.viewport_size = new_size
        self.render()

    @Slot(QPointF)
    def c_move_viewport(self, move_distance: QPointF):
        self.map_center_latlng = self._set_center_latlng_for_xy(self.view_center_xy+move_distance)
        self.view_center_xy = self.view_center_xy+move_distance
        self.render()