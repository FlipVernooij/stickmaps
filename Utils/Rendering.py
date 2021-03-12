import logging
import math

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, Qt

from Models.TableModels import Station, SqlManager



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

    def __init__(self, section_id: int, section_name: str, connection_name: str = None):
        super().__init__()
        self.cursor_location = QPointF(0, 0)
        self.sql_manager = SqlManager(connection_name if connection_name is not None else self.SQL_MANAGER_CONNECTION_NAME)
        self.section_id = section_id
        self.section_name = section_name
        self.stations = self.sql_manager.factor(Station).get_stations_for_section(section_id)

        path_data = self.get_path(self.stations)

        self.pixmap = QPixmap(
            path_data['grid']['width']+self.MAP_PADDING,
            path_data['grid']['height']+self.MAP_PADDING
        )

        self.pixmap.fill(Qt.transparent)
        self.painter = QPainter()
        self.painter.begin(self.pixmap)
        self.painter.setRenderHint(QPainter.Antialiasing)
        #self.painter.setRenderHint(QPainter.An)

        self.pen = QPen(Qt.white, self.MAP_LINE_WIDTH)

        self.painter.setPen(self.pen)

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
                self.pen.setColor(Qt.white)
                self.painter.setPen(self.pen)
                self.painter.setBrush(Qt.white)
            self.painter.drawEllipse(e, self.MAP_STATION_DOT, self.MAP_STATION_DOT)



        self.painter.end()

    def get_pixmap(self):
        #return QPixmap(APPLICATION_ICON )
        return self.pixmap

    def get_cursor_location(self):
        return self.cursor_location.toPoint()