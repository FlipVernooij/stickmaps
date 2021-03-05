import math

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor

from Models.TableModels import Station


class CalcMixin:

    def get_line(self, azimuth: int, length: int, x_start: int = 0, y_start: int = 0) -> list:
        point_start = QPoint(x_start, y_start)
        point_end = self.get_point(azimuth, length)
        if x_start != 0:
            point_end.setX(point_end.x()+x_start)
        if y_start != 0:
            point_end.setX(point_end.y()+y_start)

        return [point_start, point_end]

    def get_point(self, azimuth: float, length: float):
        return QPoint(xpos=math.cos(azimuth) * length, ypos=math.sin(azimuth) * length)


class DragImage(CalcMixin):

    def __init__(self, section_id: int, section_name: str):
        self.section_id = section_id
        self.section_name = section_name
        self.stations = Station.get_stations_for_section(section_id)

        lines = []
        x = 0
        y = 0
        max_x = 0
        min_x = 0
        max_y = 0
        min_y = 0
        for station in self.stations:


            last_line = self.get_line(
                station['azimuth_out_avg'],
                station['length_out'],
                x,
                y
            )
            x = last_line[1].x()
            y = last_line[1].y()
            min_x = x if x < min_x else min_x
            max_x = x if x > max_x else max_x
            min_y = y if y < min_y else min_y
            max_y = y if y > max_y else max_y
            lines.append(last_line)

        self.pixmap = QPixmap(max_x + abs(min_x) + 20, max_y + abs(min_y) + 20)
        self.painter = QPainter()
        self.pen = QPen((QColor(69, 86, 96)), 1)
        self.painter.begin(self.pixmap)
        for line in lines:
            s = line[0]
            e = line[1]
            s.setX(s.x()+abs(min_x)+10)
            s.setY(s.y()+abs(min_y)+10)
            e.setX(e.x()+abs(min_x)+10)
            e.setY(e.y()+abs(min_y)+10)
            self.painter.drawLine(s, e)

        self.painter.end()

    def get_pixmap(self):
        return self.pixmap