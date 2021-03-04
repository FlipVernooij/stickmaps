import math

from PySide6.QtCore import QPoint
from PySide6.QtGui import QPixmap

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
        last_line = ['', QPoint(0, 0)]

        max_x = 0
        min_x = 0

        max_y
        min_y
        for station in self.stations:

            last_line = self.get_line(
                station['azimuth_out_avg'],
                station['length_out'],
                last_line[1].x(),
                last_line[1].y()
            )
            lines.append(last_line)

        self.pixmap = QPixmap()
