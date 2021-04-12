# QGraphicsScene
import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsScene

from Gui.Scene.Overlays import SatelliteOverlay
from Models.TableModels import SqlManager, ImportSurvey, ImportLine, ImportStation, ProjectSettings


class MainScene(QGraphicsScene):

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.log = logging.getLogger(__name__)
        self._init_database_objects()
        self._overlays = {}  # Contains all the overlays required for this Scene.

        """ Init Scene configuration """
        #self.setSceneRect(self.parent().viewport().rect())
        #self.set_background_color(Qt.white)

        """ Init project properties """
        self.current_project = None  # list holding the current project data.
        self.project_latlng_set = False  # set to true when the latitude and longitude are set for this project

        self.scene_center_latlng = None
        self.scene_center_xy = None

        """ Add default overlays """
        self.add_overlay(object=SatelliteOverlay(self), position=0)  # Used for rendering satelite images as a background.
        #
        # self.map_group = QGraphicsItemGroup()
        # self.addItem(self.map_group)
        # self.overlay = OverlayGoogleMaps(self, self.map_group)
        #
        # self.log.info('Using default lat/lng from constants file.')
        # lat = Preferences.get('default_latitude', DEFAULT_LATITUDE, float)
        # lng = Preferences.get('default_longitude', DEFAULT_LONGITUDE, float)
        #
        #
        # lat_lng = QPointF(lat, lng)

    def _init_database_objects(self):
        self._sql_manager = SqlManager()
        self.db_project = self._sql_manager.factor(ProjectSettings)
        self.db_import_survey = self._sql_manager.factor(ImportSurvey)
        self.db_import_line = self._sql_manager.factor(ImportLine)
        self.db_import_station = self._sql_manager.factor(ImportStation)

    # @todo This could be done in a better way right.. maybe connect to a "reload" signal within the main window?
    def reload(self):
        self.current_project = self.db_project.get()
        self.parent().s_project_changed.emit(self.current_project)

        # if self.current_project['latitude'] != '' and self.current_project['longitude'] != '':
        #     self.project_latlng_set = True
        # else:
        #     self.project_latlng_set = False
        #     self.current_project['latitude'] = 0
        #     self.current_project['longitude'] = 0
        #
        # self.set_scene_center(latitude=self.current_project['latitude'], longitude=self.current_project['longitude'])

        self.log.info(f'MainScene.reload() loaded project {self.current_project["project_name"]} (this should be a signal..)')

    def set_background_color(self, color):
        self.setBackgroundBrush(color)

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
