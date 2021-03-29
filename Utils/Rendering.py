import logging
import math
from datetime import datetime

from PySide6.QtCore import QPointF, QPoint
from PySide6.QtGui import QPixmap, QPainter, QPen, Qt
from PySide6.QtWidgets import QGraphicsScene, QGraphicsSceneDragDropEvent, QGraphicsPixmapItem, QGraphicsItemGroup

from Config.Constants import SURVEY_DIRECTION_OUT, SURVEY_DIRECTION_IN, DEFAULT_LATITUDE, DEFAULT_LONGITUDE
from Models.TableModels import ImportStation, SqlManager, ImportLine, ImportSurvey
from Utils.Logging import Track
from Utils.Map import StationItem, OverlayGoogleMaps
from Utils.Settings import Preferences


class CalcMixin:

    def __init__(self):

        self.log = logging.getLogger(__name__)
        self.one_meter_is_points = 5

    def get_plane_y(self, y: float, grid_info: dict) -> float:
        """
           grid_info =
            {
                "min": min,
                "max": max,
                "zero_at": QPointF(),
                "width": abs(min.x()) + abs(max.x()),
                "height": abs(min.y()) + abs(max.y())

            }
        """

        return grid_info['zero_at'].y() -y

    def get_plane_x(self, x: float, grid_info: dict) -> float:
        """
           grid_info =
            {
                "min": min,
                "max": max,
                "zero_at": QPointF(),
                "width": abs(min.x()) + abs(max.x()),
                "height": abs(min.y()) + abs(max.y())

            }
        """
        return grid_info['zero_at'].x() + x

    def get_path(self, stations: list, start_at: QPointF = QPointF(0, 0)):
        path = []
        min = QPointF(0, 0)
        max = QPointF(0, 0)

        for station in stations:
            end_at = self.get_point(station['azimuth_out_avg'], self.get_length(station['length_out']))
            end_at = start_at + end_at  # end_at is relative to the coords or start_at.
            if end_at.x() < min.x():
                min.setX(end_at.x())
            if end_at.y() < min.y():
                min.setY(end_at.y())

            if end_at.x() > max.x():
                max.setX(end_at.x())
            if end_at.y() > max.y():
                max.setY(end_at.y())

            path.append({"s": start_at, "e": end_at})
            # next start_at is this end_at
            start_at = end_at

        zero_at = QPointF(abs(min.x()), abs(max.y()))
        data = {

            "path": path,
            "grid":
                {
                    "min": min,
                    "max": max,
                    "zero_at": zero_at,
                    "width": abs(min.x())+abs(max.x()),
                    "height": abs(min.y())+abs(max.y())
                }
        }
        self.log.debug(f"Grid info is: {data['grid']}")
        return data

    def get_length(self, length: float):
        return self.one_meter_is_points * length

    def get_line(self, azimuth: int, length: int, x_start: int = 0, y_start: int = 0) -> list:
        point_start = QPointF(x_start, y_start)
        point_end = self.get_point(azimuth, length) + point_start

        return [point_start, point_end]

    def get_point(self, azimuth: float, length: float):
        radian = math.radians(azimuth)
        x = math.sin(radian)
        y = math.cos(radian)
        return QPointF(length * x, length * y)


class DragImage(CalcMixin):
    SQL_MANAGER_CONNECTION_NAME = 'DrawImage'

    MAP_PADDING = 50

    MAP_LINE_WIDTH = 4

    MAP_STATION_DOT = 4

    MAP_LINE_COLOR = Qt.gray

    def __init__(self, line_id: int, connection_name: str = None):
        super().__init__()
        self.cursor_location = QPointF(0, 0)
        self.sql_manager = SqlManager(connection_name if connection_name is not None else self.SQL_MANAGER_CONNECTION_NAME)
        self.line = self.sql_manager.factor(ImportLine).get(line_id)
        self.stations = self.sql_manager.factor(ImportStation).get_all(line_id)

        path_data = self.get_path(self.stations)

        self.pixmap = QPixmap(
            path_data['grid']['width']+self.MAP_PADDING,
            path_data['grid']['height']+self.MAP_PADDING
        )

        self.pixmap.fill(Qt.transparent)
        self.painter = QPainter()
        self.painter.begin(self.pixmap)
        self.painter.setRenderHint(QPainter.Antialiasing)

        self.pen = QPen(self.MAP_LINE_COLOR, self.MAP_LINE_WIDTH)

        self.painter.setPen(self.pen)

        for i, line in enumerate(path_data['path']):
            s = QPointF(line['s'].x(), line['s'].y())
            e = QPointF(line['e'].x(), line['e'].y())
            s.setX(self.get_plane_x(s.x(), path_data['grid']) + (self.MAP_PADDING / 2))
            s.setY(self.get_plane_y(s.y(), path_data['grid']) + (self.MAP_PADDING / 2))
            e.setX(self.get_plane_x(e.x(), path_data['grid']) + (self.MAP_PADDING / 2))
            e.setY(self.get_plane_y(e.y(), path_data['grid']) + (self.MAP_PADDING / 2))
            self.painter.drawLine(s, e)
            if (i == 0 and self.line['direction'] == SURVEY_DIRECTION_IN) \
                or (i == len(path_data['path'])-1 and self.line['direction'] == SURVEY_DIRECTION_OUT):
                self.cursor_location = s
                self.pen.setColor(Qt.red)
                self.painter.setPen(self.pen)
                self.painter.setBrush(Qt.red)
                self.painter.drawEllipse(s, self.MAP_STATION_DOT, self.MAP_STATION_DOT)
                self.pen.setColor(self.MAP_LINE_COLOR)
                self.painter.setPen(self.pen)
                self.painter.setBrush(self.MAP_LINE_COLOR)
            else:
                self.painter.drawEllipse(e, self.MAP_STATION_DOT, self.MAP_STATION_DOT)



        self.painter.end()

    def get_pixmap(self):
        return self.pixmap

    def get_cursor_location(self):
        return self.cursor_location.toPoint()


# QGraphicsScene
class MapScene(QGraphicsScene):
    """
        This will combine all underneath layers to a single response..
    """
    def __init__(self, parent_view):
        super().__init__(parent=parent_view)
        self.log = logging.getLogger(__name__)
        self.parent_view = parent_view
        self._sql_manager = SqlManager()
        self.import_survey = self._sql_manager.factor(ImportSurvey)
        self.import_line = self._sql_manager.factor(ImportLine)
        self.import_station = self._sql_manager.factor(ImportStation)

        self.overlay = OverlayGoogleMaps(self)

        lat = Preferences.get('default_latitude', DEFAULT_LATITUDE, float)
        lng = Preferences.get('default_longitude', DEFAULT_LONGITUDE, float)
        lat_lng = QPointF(lat, lng)

        """
         @todo this should be done threaded
         @todo I need to detect screen-size and make it fill the screen...
        """
        group = QGraphicsItemGroup()

        group.addToGroup(self.overlay.get_tile(lat_lng))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_NORTH))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_NORTH_EAST))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_EAST))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_SOUTH_EAST))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_SOUTH))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_SOUTH_WEST))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_WEST))
        group.addToGroup(self.overlay.get_surrounding_tile_heading(lat_lng, self.overlay.TILE_NORTH_WEST))

        self.addItem(group)
        #self.log.warning(f'North latlng returned: {north}')
        #self.addItem(self.overlay.get_tile(north))



    def load_map_from_database(self):
        """
        Called from the __init__ and called when an file is openend.
        """
        return True

    def append_import_line(self, line_row: dict, survey_row: dict, cursor_position: QPoint):
        """
        Called on the dropEvent, a new line from the import tree is added to the map.
        """
        year = datetime.fromtimestamp(survey_row).year

        stations = self.import_station.get_all(line_row['line_id'])
        start_at = QPointF(xpos=Preferences.get('default_latitude', DEFAULT_LATITUDE),
                           ypos=Preferences.get('default_longitude', DEFAULT_LONGITUDE))
        for station, index in enumerate(stations):
            if index == 0:
                if station['latitude'] is not None and station['longitude'] is not None:
                    start_at = QPointF(xpos=station['latitude'], ypos=station['longitude'])

            item = StationItem(start_at, station, year)
            item.render_station()
            item.render_line()

            item.render_markers()
            item.render_name()
            item.render_depth()
            item.render_length()

 # Drag & drop event
    def dragEnterEvent(self, event) -> None:
        event.accept()
        return None

    def dragLeaveEvent(self, event) -> None:
        event.accept()
        return None

    def dragMoveEvent(self, event) -> None:
        event.accept()
        return None

    def dropEvent(self, event):
        super().dropEvent(event)
        mime = event.mimeData()
        if mime.property('survey_id') is None:
            event.ignore()  # when we drop a random document from outside the application the screen (by accident)
            return
        survey = self.import_survey.get(int(mime.property('survey_id')))
        line = self.import_line.get(int(mime.property('line_id')))
        mousePosition = event.pos()
        self.append_import_line(line, survey, mousePosition)
        # event.accept()
        return None


class LineLayer():
    """
        This is the bottom layer if the "image"
        It only renders the "line"
    """

class StationLayer():
    """
        This will be the layer that renders all the stations circels.
    """

class TextLayer():
    """
        This will be the layer that renders all the different station names, notes and other crap.
    """

class InteractiveLayer():
    """
        This will be the interactive layer, and will be responsible for all the different interactions.
    """


class ImageTest(CalcMixin):

    LOOP_TIMES = 1

    SQL_MANAGER_CONNECTION_NAME = 'ImageTest'

    MAP_PADDING = 50

    MAP_LINE_WIDTH = 4

    MAP_STATION_DOT = 4

    MAP_LINE_COLOR = Qt.gray

    def __init__(self, line_id: int, line_name: str, connection_name: str = None):
        self.log = logging.getLogger(__name__)
        super().__init__()
        self.sql_manager = SqlManager(
            connection_name if connection_name is not None else self.SQL_MANAGER_CONNECTION_NAME

        )
        self.line_id = line_id
        self.line_name = line_name
        self.stations = []
        Track.timer_start('total')
        Track.timer_start('sql')
        for i in range(self.LOOP_TIMES):
            self.stations.extend(self.sql_manager.factor(ImportStation).get_all(line_id))

        self.log.info(f'Drawing {len(self.stations)} stations to single pixmap')
        self.log.info(f'SQL run for {Track.timer_end("sql")}')

        Track.timer_start('path')
        path_data = self.get_path(self.stations)
        self.log.info(f'PATHING run for {Track.timer_end("path")}')

        Track.timer_start('init')
        self.pixmap = QPixmap(
            path_data['grid']['width'] + self.MAP_PADDING,
            path_data['grid']['height'] + self.MAP_PADDING
        )

        self.pixmap.fill(Qt.transparent)
        self.painter = QPainter()
        self.painter.begin(self.pixmap)
        self.painter.setRenderHint(QPainter.Antialiasing)

        self.pen = QPen(self.MAP_LINE_COLOR, self.MAP_LINE_WIDTH)

        self.painter.setPen(self.pen)
        self.log.info(f'Init pixmap took: {Track.timer_end("init")}')
        Track.timer_start('draw')
        for i, line in enumerate(path_data['path']):
            s = QPointF(line['s'].x(), line['s'].y())
            e = QPointF(line['e'].x(), line['e'].y())
            s.setX(self.get_plane_x(s.x(), path_data['grid']) + (self.MAP_PADDING / 2))
            s.setY(self.get_plane_y(s.y(), path_data['grid']) + (self.MAP_PADDING / 2))
            e.setX(self.get_plane_x(e.x(), path_data['grid']) + (self.MAP_PADDING / 2))
            e.setY(self.get_plane_y(e.y(), path_data['grid']) + (self.MAP_PADDING / 2))
            self.painter.drawLine(s, e)
            if i == 0:
                self.cursor_location = s
                self.pen.setColor(Qt.red)
                self.painter.setPen(self.pen)
                self.painter.setBrush(Qt.red)
                self.painter.drawEllipse(s, self.MAP_STATION_DOT, self.MAP_STATION_DOT)
                self.pen.setColor(self.MAP_LINE_COLOR)
                self.painter.setPen(self.pen)
                self.painter.setBrush(self.MAP_LINE_COLOR)
            self.painter.drawEllipse(e, self.MAP_STATION_DOT, self.MAP_STATION_DOT)
        self.log.info(f'DRAW run for {Track.timer_end("draw")}')
        Track.timer_start('end')
        self.painter.end()
        self.log.info(f'End painter took: {Track.timer_end("end")}')
        self.log.info(f'Total render took: {Track.timer_end("total")}')

    def get_pixmap(self):
        return self.pixmap

    def get_cursor_location(self):
        return self.cursor_location.toPoint()
