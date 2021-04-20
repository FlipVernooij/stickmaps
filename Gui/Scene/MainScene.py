# QGraphicsScene
import logging
import math

from PySide6.QtCore import Qt, QRect, QSize, Slot, QPointF, Signal
from PySide6.QtWidgets import QGraphicsScene, QGraphicsItem

from Gui.Scene.Overlays import SatelliteOverlay, GridOverlay
from Models.TableModels import SqlManager, ImportSurvey, ImportLine, ImportStation, ProjectSettings

"""
Alrighty:
I have restructured the mapview to something more logic

We will work with Overlays from now stating with the SatelliteOverlay on the bottom.
I have created the "SatelliteOverlay" to start with and am getting close to something usable.

ATM: I am fetching the tiles around the centerpoint of the map (lat/lng from projectSettings) correctly.
    Yet I need to place them at the right coordinates in the view.
    Then I need to work with the zooming.
    
    I made the zoom from 0 till 20.9 using the float as an extra zoom option.
"""
class MainScene(QGraphicsScene):

    # max = 256*math.pow(2, 21) (256 is world_tiles, 21=zoom_level)
    WORLD_RECT = QRect(0, 0, 536870912, 536870912)

    """
    Sets the background color of the scene.
    """
    s_set_background_color = Signal(object)

    """
        Called when the scene is resized (enlarged) this is NOT emitted when the view resizes.
        old_size: QRect
        new_size: QRect
    """
    s_scene_resize = Signal(QRect, QRect)

    @Slot(object)
    def c_set_background_color(self, color):
        self.setBackgroundBrush(color)

    @Slot(dict)
    def c_load_project(self, project: dict):
        self.log.debug(f'MainScene: Loading new project: "{project["project_name"]}"')
        self.s_set_background_color.emit(Qt.white)

    @Slot(QSize, QSize)
    def c_view_resize(self, old_size: QSize, new_size: QSize):
        pass
        if new_size.width() > self.sceneRect().width() or new_size.height() > self.sceneRect().height():
            self.log.debug("Scene resize called, enlarging scene")
            # we have to resize the scene
            old_rect = self.sceneRect()
            self.setSceneRect(QRect(0, 0, new_size.width(), new_size.height()))
            self.s_scene_resize.emit(old_rect, self.sceneRect())
        else:
            self.log.debug(f"Scene resize called: scene is bigger then view")
            # we don't do anything.
            pass


    def view_rect(self) -> QRect:
        return self.parent().mapToScene(self.parent().viewport().rect()).boundingRect()

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.log = logging.getLogger(__name__)
        self.setSceneRect(self.WORLD_RECT)
        # Connect signals
        parent.parent().s_load_project.connect(self.c_load_project)
        self.s_set_background_color.connect(self.c_set_background_color)
        parent.s_view_resize.connect(self.c_view_resize)


        #self._init_database_objects()
        self._overlays = {}  # Contains all the overlays required for this Scene.


        """ Init project properties """
        self.current_project = None  # list holding the current project data.


        """ Add default overlays """
        #self.add_overlay(object=SatelliteOverlay(self), position=10)  # Used for rendering satelite images as a background.
        self.add_overlay(object=GridOverlay(self), position=20)
        #
        # self.parent().s_move_viewport.connect(self.c_move_viewport)

    # def _init_database_objects(self):
    #     self._sql_manager = SqlManager()
    #     self.db_project = self._sql_manager.factor(ProjectSettings)
    #     self.db_import_survey = self._sql_manager.factor(ImportSurvey)
    #     self.db_import_line = self._sql_manager.factor(ImportLine)
    #     self.db_import_station = self._sql_manager.factor(ImportStation)
    #

    @property
    def main_application(self):
        return self.parent().parent()

    def add_overlay(self,  object, name: str = None, position: int = None):
        """
            By making this a method, it becomes possible to in a future moment add custom overlays.
            We can even allow users to do so...
        :param object:
        :param name:
        :param position:
        :return:
        """
        if position is None:
            position = len(self._overlays)
        if name is None:
            name = type(object).__name__

        self._overlays[name] = {
            "object": object,
            "position": position
        }

        self.addItem(object)

    def get_overlay(self, name: str):
        return self._overlays[name]

    def remove_overlay(self, name: str):
        del self._overlays[name]
    #
    # # I should propably move these somewhere... yet I don't know where yet
    # def meters_per_pixel(self, zoom_level: float = None, latitude: float = None):
    #     if zoom_level is None:
    #         zoom_level = self.get_zoom()
    #     if latitude is None:
    #         try:
    #             if self.current_project['latitude'] is float:
    #                 latitude = self.current_project['latitude']
    #             else:
    #                 raise KeyError('bla')
    #         except KeyError:
    #             latitude = 20.4916217646394  # we need to use a dummy value (eden)
    #
    #     return 156543.03392 * math.cos(latitude * math.pi / 180) / math.pow(2, zoom_level)
    #
    # # signals
    # @Slot(QSize)
    # def c_move_viewport(self, offset: QSize):
    #     pass
    #
    # @Slot(float, float, QPointF)
    # def c_zoom_viewport(self, old_zoom: float, zoom_level: float,  cursor_pos: QPointF):
    #   pass
    #
    # @Slot(QRect, QSize)
    # def c_resize_scene(self, rect: QRect, offset: QSize):
    #     """
    #
    #     :param rect: the new rectangle dimensions
    #     :param offset: the x/y offset between the old and new retangle
    #     :return:
    #     """
    #     self.setSceneRect(rect)
    #     self.parent().s_move_viewport.emit(offset)


    # events


 #
 #    def reload(self):
 #        self.overlay.reload()
 #
 #    def load_map_from_database(self):
 #        """
 #        Called from the __init__ and called when an file is openend.
 #        """
 #        return True
 # #
 #    def append_import_line(self, line_row: dict, survey_row: dict, cursor_position: QPoint):
 #        """
 #        Called on the dropEvent, a new line from the import tree is added to the map.
 #        """
 #        year = datetime.fromtimestamp(survey_row).year
 #
 #        stations = self.import_station.get_all(line_row['line_id'])
 #        start_at = QPointF(xpos=Preferences.get('default_latitude', DEFAULT_LATITUDE),
 #                           ypos=Preferences.get('default_longitude', DEFAULT_LONGITUDE))
 #        for station, index in enumerate(stations):
 #            if index == 0:
 #                if station['latitude'] is not None and station['longitude'] is not None:
 #                    start_at = QPointF(xpos=station['latitude'], ypos=station['longitude'])
 #
 #            item = StationItem(start_at, station, year)
 #            item.render_station()
 #            item.render_line()
 #
 #            item.render_markers()
 #            item.render_name()
 #            item.render_depth()
 #            item.render_length()
 #
 # # Drag & drop event
 #    def dragEnterEvent(self, event) -> None:
 #        event.accept()
 #        return None
 #
 #    def dragLeaveEvent(self, event) -> None:
 #        event.accept()
 #        return None
 #
 #    def dragMoveEvent(self, event) -> None:
 #        event.accept()
 #        return None
 #
 #    def dropEvent(self, event):
 #        super().dropEvent(event)
 #        mime = event.mimeData()
 #        if mime.property('survey_id') is None:
 #            event.ignore()  # when we drop a random document from outside the application the screen (by accident)
 #            return
 #        survey = self.import_survey.get(int(mime.property('survey_id')))
 #        line = self.import_line.get(int(mime.property('line_id')))
 #        mousePosition = event.pos()
 #        self.append_import_line(line, survey, mousePosition)
 #        # event.accept()
 #        return None
 #
