from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import QMessageBox, QApplication

from Config.Constants import SQL_TABLE_SURVEYS, SQL_TABLE_SECTIONS, SQL_TABLE_STATIONS, TREE_DARK_ICON_SURVEY,\
    TREE_DARK_ICON_SECTION, TREE_DARK_ICON_STATION, TREE_LIGHT_ICON_SURVEY, TREE_LIGHT_ICON_SECTION, \
    TREE_LIGHT_ICON_STATION
from .TableModels import Survey, Section, Station


class SectionItem(QStandardItem):

    def __init__(self, icon, row):
        super().__init__(icon, row)
        self.setDragEnabled(True)
        self.item_type = SurveyCollection.ITEM_TYPE_SECTION


    def event(self, event):
        foo = 1





class SurveyCollection(QStandardItemModel):

    ITEM_TYPE_STATION = 1
    ITEM_TYPE_SECTION = 2
    ITEM_TYPE_SURVEY = 4

    def __init__(self):
        super(SurveyCollection, self).__init__()
        self.load_model()

    def load_model(self, survey_id: int = None):
        if QApplication.instance().palette().text().color().name() == '#ffff':
            # probably dark theme
            survey_icon = QIcon(TREE_DARK_ICON_SURVEY)
            section_icon = QIcon(TREE_DARK_ICON_SECTION)
            station_icon = QIcon(TREE_DARK_ICON_STATION)
        else:
            # probably light theme
            survey_icon = QIcon(TREE_LIGHT_ICON_SURVEY)
            section_icon = QIcon(TREE_LIGHT_ICON_SECTION)
            station_icon = QIcon(TREE_LIGHT_ICON_STATION)

        if survey_id is None:
            survey_rows = Survey.fetch(f'SELECT survey_id, survey_name, device_name FROM {SQL_TABLE_SURVEYS} ORDER BY survey_id DESC', [])
        else:
            survey_rows = [Survey.get_survey(survey_id)]
        for survey_row in survey_rows:
            survey = QStandardItem(survey_icon, survey_row['survey_name'])
            survey.setDragEnabled(False)
            survey.survey_id = survey_row['survey_id']
            survey.item_type = self.ITEM_TYPE_SURVEY
            section_rows = Section.fetch(f'SELECT section_id, section_name FROM {SQL_TABLE_SECTIONS} WHERE survey_id={survey_row["survey_id"]}')
            for section_row in section_rows:
                section = SectionItem(section_icon, section_row['section_name'])

                section.survey_id = survey_row['survey_id']
                section.section_id = section_row['section_id']

                station_rows = Station.fetch(
                    f'SELECT station_id, station_name FROM {SQL_TABLE_STATIONS} WHERE section_id={section_row["section_id"]}')
                for station_row in station_rows:
                    station = QStandardItem(station_icon,  station_row['station_name'])
                    station.setDragEnabled(False)
                    station.item_type = self.ITEM_TYPE_STATION
                    station.survey_id = survey_row['survey_id']
                    station.section_id = section_row['section_id']
                    station.station_id = station_row['station_id']
                    section.appendRow(station)
                survey.appendRow(section)
            if survey_id is None:
                self.appendRow(survey)
            else:
                self.insertRow(0, survey)

    def reload_model(self):
        self.removeRows(0, self.rowCount())
        self.load_model()


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

    def reload_stations(self, section_item: QStandardItem) -> int:
        section_id = section_item.section_id
        item = section_item
        count = item.rowCount()

        station_rows = Station.fetch(f'SELECT station_id, station_name FROM {SQL_TABLE_STATIONS} WHERE section_id={section_id}')

        for i in range(count):
            station_item = item.child(i)
            if station_rows[i]['station_id'] == station_item.station_id:
                self.setData(station_item.index(), station_rows[i]['station_name'])
            else:
                QMessageBox.warning('Error', f"Mmm station mismatch {station_rows[i]['station_id']} != {station_item.station_id}")
                break

    def update_station(self, data: dict, index):
        row = data.copy()
        station_id = row['section_id']
        del row['station_id']
        Station.update_station(row, station_id)
        self.setData(index, row['station_name'])
        return

    def delete_station(self, item: QStandardItem) -> int:
        station_id = item.station_id
        num_rows = Station.delete_station(station_id)
        self.removeRows(item.row(), 1, item.parent().index())
        return num_rows

