from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import QMessageBox

from Config.Constants import TREE_ICON_SURVEY, TREE_ICON_SECTION, TREE_ICON_POINT, SQL_TABLE_SURVEYS, \
    SQL_TABLE_SECTIONS, SQL_TABLE_POINTS
from .TableModels import Survey, Section, Point

class SurveyCollection(QStandardItemModel):

    ITEM_TYPE_POINT = 1
    ITEM_TYPE_SECTION = 2
    ITEM_TYPE_SURVEY = 4

    def __init__(self):
        super(SurveyCollection, self).__init__()

        #Survey.connect(Survey(), Survey.dataChanged, lambda: self.redraw_survey())
        #Section.connect(Section(), Section.dataChanged, lambda: self.redraw_section())

        self.load_model()

    def load_model(self, survey_id: int = None):
        survey_icon = QIcon(TREE_ICON_SURVEY)
        section_icon = QIcon(TREE_ICON_SECTION)
        point_icon = QIcon(TREE_ICON_POINT)
        if survey_id is None:
            survey_rows = Survey.fetch(f'SELECT survey_id, survey_name, device_name FROM {SQL_TABLE_SURVEYS} ORDER BY survey_id DESC', [])
        else:
            survey_rows = [Survey.get_survey(survey_id)]
        for survey_row in survey_rows:
            survey = QStandardItem(survey_icon, survey_row['survey_name'])
            survey.survey_id = survey_row['survey_id']
            survey.item_type = self.ITEM_TYPE_SURVEY
            section_rows = Section.fetch(f'SELECT section_id, section_name FROM {SQL_TABLE_SECTIONS} WHERE survey_id={survey_row["survey_id"]}')
            for section_row in section_rows:
                section = QStandardItem(section_icon, section_row['section_name'])
                section.survey_id = survey_row['survey_id']
                section.section_id = section_row['section_id']
                section.item_type = self.ITEM_TYPE_SECTION
                point_rows = Point.fetch(
                    f'SELECT point_id, point_name FROM {SQL_TABLE_POINTS} WHERE section_id={section_row["section_id"]}')
                for point_row in point_rows:
                    point = QStandardItem(point_icon,  point_row['point_name'])
                    point.item_type = self.ITEM_TYPE_POINT
                    point.survey_id = survey_row['survey_id']
                    point.section_id = section_row['section_id']
                    point.point_id = point_row['point_id']
                    section.appendRow(point)
                survey.appendRow(section)
            if survey_id is None:
                self.appendRow(survey)
            else:
                self.insertRow(0, survey)

    def append_survey_from_db(self, survey_id):
        self.load_model(survey_id)

    def update_survey(self, data: dict, index):
        row = data.copy()
        survey_id = row['survey_id']
        del row['survey_id']
        Survey.update_survey(row,  survey_id)
        ## We need to call setData() on self and not on the item.
        ## the DataChanged doesn't bubble up as you would expect.
        self.setData(index, row['survey_name'])
        return

    def delete_survey(self, item: QStandardItem) -> int:
        survey_id = item.survey_id
        num_rows = Survey.delete_survey(survey_id)

        self.removeRows(item.row(), 1)

        return num_rows

    def reload_sections(self, survey_item: QStandardItem) -> int:
        survey_id = survey_item.survey_id
        item = survey_item
        count = item.rowCount()

        section_rows = Section.fetch(f'SELECT section_id, section_name FROM {SQL_TABLE_SECTIONS} WHERE survey_id={survey_id}')

        for i in range(count):
            section_item = item.child(i)
            if section_rows[i]['section_id'] == section_item.section_id:
                self.setData(section_item.index(), section_rows[i]['section_name'])
            else:
                QMessageBox.warning('Error', f"Mmm section mismatch {section_rows[i]['section_id']} != {section_item.section_id}")
                break

    def update_section(self, data: dict, index):
        row = data.copy()
        section_id = row['section_id']
        del row['section_id']
        Section.update_section(row,  section_id)
        ## We need to call setData() on self and not on the item.
        ## the DataChanged doesn't bubble up as you would expect.
        self.setData(index, row['section_name'])
        return

    def delete_section(self, item: QStandardItem) -> int:
        section_id = item.section_id
        num_rows = Section.delete_section(section_id)
        self.removeRows(item.row(), 1, item.parent().index())
        return num_rows

    def reload_points(self, section_item: QStandardItem) -> int:
        section_id = section_item.section_id
        item = section_item
        count = item.rowCount()

        point_rows = Point.fetch(f'SELECT point_id, point_name FROM {SQL_TABLE_POINTS} WHERE section_id={section_id}')

        for i in range(count):
            point_item = item.child(i)
            if point_rows[i]['point_id'] == point_item.point_id:
                self.setData(point_item.index(), point_rows[i]['point_name'])
            else:
                QMessageBox.warning('Error', f"Mmm point mismatch {point_rows[i]['point_id']} != {point_item.point_id}")
                break

    def update_point(self, data: dict, index):
        row = data.copy()
        point_id = row['section_id']
        del row['point_id']
        Point.update_point(row,  point_id)
        ## We need to call setData() on self and not on the item.
        ## the DataChanged doesn't bubble up as you would expect.
        self.setData(index, row['point_name'])
        return

