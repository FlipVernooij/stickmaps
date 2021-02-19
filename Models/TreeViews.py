from PySide6.QtCore import QAbstractProxyModel, QAbstractItemModel, Signal, QModelIndex
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtSql import QSqlTableModel, QSqlQueryModel, QSqlDatabase, QSqlQuery

from Config.Constants import TREE_ICON_SURVEY, TREE_ICON_SECTION, TREE_ICON_POINT, SQL_TABLE_SURVEYS, \
    SQL_TABLE_SECTIONS, SQL_TABLE_POINTS
from .TableModels import Survey, Section, Point


class QItemModel(object):
    pass


class SurveyCollection(QStandardItemModel):

    def __init__(self):
        super(SurveyCollection, self).__init__()

        #Survey.connect(Survey(), Survey.dataChanged, lambda: self.redraw_survey())
        #Section.connect(Section(), Section.dataChanged, lambda: self.redraw_section())

        self.load_model()

    def load_model(self):
        db = QSqlDatabase.database()
        survey_icon = QIcon(TREE_ICON_SURVEY)
        section_icon = QIcon(TREE_ICON_SECTION)
        point_icon = QIcon(TREE_ICON_POINT)

        survey_rows = Survey.fetch(f'SELECT survey_id, survey_name, device_name FROM {SQL_TABLE_SURVEYS}', [])
        for survey_row in survey_rows:
            survey = QStandardItem(survey_icon, survey_row['survey_name'])
            survey.survey_id = survey_row['survey_id']
            section_rows = Section.fetch(f'SELECT section_id, section_name FROM {SQL_TABLE_SECTIONS} WHERE survey_id={survey_row["survey_id"]}')
            for section_row in section_rows:
                section = QStandardItem(section_icon, section_row['section_name'])
                section.survey_id = survey_row['survey_id']
                section.section_id = section_row['section_id']
                point_rows = Point.fetch(
                    f'SELECT point_id, point_reference_id FROM {SQL_TABLE_POINTS} WHERE section_id={section_row["section_id"]}')
                for point_row in point_rows:
                    point = QStandardItem(point_icon, f"Point {point_row['point_reference_id']}")
                    point.survey_id = survey_row['survey_id']
                    point.section_id = section_row['section_id']
                    point.point_id = point_row['point_id']
                    section.appendRow(point)
                survey.appendRow(section)
            self.appendRow(survey)

    def update_survey(self, data: dict, index):
        row = data.copy()
        survey_id = row['survey_id']
        del row['survey_id']
        Survey.update(SQL_TABLE_SURVEYS, row, 'survey_id=?', [survey_id])
        ## We need to call setData() on self and not on the item.
        ## the DataChanged doesn't bubble up as you would expect.
        self.setData(index, row['survey_name'])
        return
