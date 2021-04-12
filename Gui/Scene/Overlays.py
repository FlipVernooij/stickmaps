import logging

from PySide6.QtCore import QPointF, Slot, QSize
from PySide6.QtWidgets import QGraphicsItemGroup

from Gui.Scene.Providers.Satellite import GoogleMapsProvider


class SatelliteOverlay(QGraphicsItemGroup):

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        self.map_view = self.parent().parent()
        self.log = logging.getLogger(__name__)
        self._provider = None

        # is the overlay enabled (do we have lat/lng?)
        self.is_enabled = False
        # is the overlay visible or hidden?
        self.is_visible = False
        # the center of the map
        self.map_center = None
        self.viewport_size = None # I can not set this on __init__, this is done by the c_resize_viewport slot which is also called before displaying the application at boot.

        self.zoom_level = self.map_view.get_zoom()
        self.zoom_center = None  # zooming should occur at cursor,.. or map_center when done with slider or such

        self.map_view.s_project_changed.connect(self.c_project_changed)
        self.map_view.s_toggle_satellite.connect(self.c_toggle_visibility)

        self.map_view.s_resize_viewport.connect(self.c_resize_viewport)
        self.map_view.s_zoom_viewport.connect(self.c_zoom_viewport)


        self.show()

    @Slot(dict)
    def c_project_changed(self, project: dict):
        """
            If anything in the projectSettings changed, this method is called.

        :param project:
        :return:
        """

        if project['latitude'] != '' and project['longitude'] != '':
            center = QPointF(project['latitude'], project['longitude'])
            if center != self.map_center:
                self.map_center = center
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
        self.zoom_level = zoom
        self.zoom_center = cursor_position
        self.render()

    @Slot(QSize)
    def c_resize_viewport(self, new_size: QSize):
        self.viewport_size = new_size
        self.render()

    def show(self):
        self.log.debug(f'Showing SatelliteOverlay')
        self.is_visible = True
        self.setVisible(True)  # call on parent
        self.render()

    def hide(self):
        self.log.info(f'Hidding SatelliteOverlay')
        self.is_visible = False
        self.setVisible(False)  # call on parent

    def render(self):
        if self.is_enabled is True and self.is_visible is True:
            self.get_provider().render()

    def get_provider(self):
        if self._provider is None:
            self._provider = GoogleMapsProvider(self)
        return self._provider

    def parent(self):
        return self._parent