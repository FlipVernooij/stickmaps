import pytest

from PySide6.QtCore import QPointF, QRect, QPoint, QSize

from Config.Constants import DEGREES_N, DEGREES_E, DEGREES_SW
from Gui.Scene.CoordSystem import TranslateCoordinates



class TestTranslateCoordinates:

    @pytest.mark.parametrize("from_latlng,distance_in_meters,heading_degrees,expected", [
        (
            QPointF(43.09963063166313, -78.0664504873053),
            1000,
            DEGREES_N,
            QPointF(43.10862383530038, -78.0664504873053),
        ), (
            QPointF(43.09963063166313, -78.0664504873053),
            5000,
            DEGREES_N,
            QPointF(43.144596649849355, -78.0664504873053),
        ), (
            # Dhaka - Hazrat Shahjalal International Airport
            QPointF(23.84488019878837, 90.403025407734),
            100000,
            DEGREES_E,
            QPointF(23.84176078410995, 91.38625673916818),

        ), (
            # Dhaka - Hazrat Shahjalal International Airport
            QPointF(23.84488019878837, 90.403025407734),
            10000,
            DEGREES_SW,
            QPointF(23.781273069135427, 90.33353340490616),

        )
    ])
    def test_latlng_at_distance(self, from_latlng: QPointF, distance_in_meters: float, heading_degrees: float, expected: QPointF):
        """
        @todo I did some approximate validation on google-maps, yet it is very hard to ensure this method is exact.
              I need a different source of test data that is more reliable.

        :param from_latlng:
        :param distance_in_meters:
        :param heading_degrees:
        :param expected:
        :return:
        """
        obj = TranslateCoordinates()
        actual = obj.latlng_at_distance(from_latlng, distance_in_meters, heading_degrees)
        assert actual.x() == expected.x()
        assert actual.y() == expected.y()

    @pytest.mark.parametrize("lat_lng", [
        QPointF(43.099630631663125, -78.06645048730529),
        QPointF(23.84488019878837, 90.40302540773399),
        QPointF(23.603663891906972, 69.34316402174206),
        QPointF(29.221275527271153, 51.47385742013855)
    ])
    def test_xy_latlng_conversion(self, lat_lng):
        obj = TranslateCoordinates()
        xy = obj.latlng_2_xy(lat_lng)
        actual = obj.xy_2_latlng(xy)
        assert actual.x() == lat_lng.x(), "Latitude does not match"
        assert actual.y() == lat_lng.y(), "Longitudate does not match"

    @pytest.mark.parametrize("lat_lng,xy", [
        (QPointF(41.849999999999994, -87.65), QPointF(68861151.00444444, 168637312.22108006),)
    ])
    def test_latlng_2_xy(self, lat_lng, xy):
        obj = TranslateCoordinates()
        actual_xy = obj.latlng_2_xy(lat_lng)
        actual_latlng = obj.xy_2_latlng(xy)
        assert actual_xy.x() == xy.x(), "X does not match"
        assert actual_xy.y() == xy.y(), "Y does not match"
        assert actual_latlng.x() == lat_lng.x(), "Latitude does not match"
        assert actual_latlng.y() == lat_lng.y(), "Longitude does not match"

    @pytest.mark.parametrize("lat_lng,size_in_meters,expected", [
        [QPointF(43.09963063166313, -78.0664504873053), QSize(500000, 500000), QRect(73623585, 172194437, 3349162, 3349162)]
    ])
    def test_xy_rect_with_center_at(self, lat_lng: QPointF, size_in_meters: QSize, expected: QRect):
        obj = TranslateCoordinates()
        actual = obj.xy_rect_with_center_at(lat_lng, size_in_meters)

        assert actual == expected, "Rect is not as expected"
