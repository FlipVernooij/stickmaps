from PySide6.QtCore import Slot
from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PySide6.QtWidgets import QApplication

from Config.Constants import TREE_DARK_ICON_SURVEY,\
    TREE_DARK_ICON_LINE, TREE_DARK_ICON_STATION, TREE_LIGHT_ICON_SURVEY, TREE_LIGHT_ICON_LINE, \
    TREE_LIGHT_ICON_STATION
from .TableModels import ImportSurvey, ImportLine, ImportStation, SqlManager, MapLine, MapStation


class ItemMixin:
    MODEL_TYPE_IMPORT = 0
    MODEL_TYPE_MAP = 1

    ITEM_TYPE_IMPORTS = QStandardItem.UserType + 5
    ITEM_TYPE_MAPS = QStandardItem.UserType + 6
    ITEM_TYPE_ROOT = QStandardItem.UserType + 10
    ITEM_TYPE_STATION = QStandardItem.UserType + 20
    ITEM_TYPE_LINE = QStandardItem.UserType + 30
    ITEM_TYPE_SURVEY = QStandardItem.UserType + 40

    DARK_ICONS = {
        ITEM_TYPE_STATION: TREE_DARK_ICON_STATION,
        ITEM_TYPE_LINE: TREE_DARK_ICON_LINE,
        ITEM_TYPE_SURVEY: TREE_DARK_ICON_SURVEY,
        ITEM_TYPE_IMPORTS: TREE_DARK_ICON_STATION,
        ITEM_TYPE_MAPS: TREE_DARK_ICON_LINE,
    }

    LIGHT_ICONS = {
        ITEM_TYPE_STATION: TREE_LIGHT_ICON_STATION,
        ITEM_TYPE_LINE: TREE_LIGHT_ICON_LINE,
        ITEM_TYPE_SURVEY: TREE_LIGHT_ICON_SURVEY,
        ITEM_TYPE_IMPORTS: TREE_LIGHT_ICON_STATION,
        ITEM_TYPE_MAPS: TREE_LIGHT_ICON_LINE,
    }

    CHILD_APPEND = 1
    CHILD_PREPEND = -1

    def get_icon(self, item_type: int) -> str:
        if QApplication.instance().palette().text().color().name() == '#ffff':
            return QIcon(self.DARK_ICONS[item_type])
        return QIcon(self.LIGHT_ICONS[item_type])


class MapStationItem(QStandardItem, ItemMixin):

    def __init__(self, parent: QStandardItem, station_row: dict):
        super().__init__(self.get_icon(self.type()), station_row['station_name'])
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(MapStation)
        self._item_data = station_row

    def type(self) -> int:
        return self.ITEM_TYPE_STATION

    def type_root(self) -> int:
        return self._parent.type_root()

    def line_id(self) -> int:
        return self._parent.line_id()

    def station_id(self) -> int:
        return self._item_data['station_id']

    def remove(self):
        self.parent().removeRow(self.row())

    def model(self):
        return self._child_model

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()


class MapLineItem(QStandardItem, ItemMixin):

    def __init__(self, parent: QStandardItem, line_row: dict):
        super().__init__(self.get_icon(self.type()), line_row['line_name'])
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(MapStation)
        self._item_data = line_row
        self._children = {}

        self.append_children()

    def type(self) -> int:
        return self.ITEM_TYPE_LINE

    def type_root(self) -> int:
        return self._parent.type_root()

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()

    def line_id(self) -> int:
        return self._item_data['line_id']

    def update(self, name: str):
        self.setText(name)

    def remove(self):
        self.parent().removeRow(self.row())

    def update_children(self):
        self.removeRows(0, self.rowCount())
        self.append_children()

    def append_children(self):
        rows = self._child_model.get_all(self.line_id())
        for row in rows:
            self._add_child(self.CHILD_APPEND, row)

    def prepend_child(self, station_id: int):
        row = self._child_model.get(station_id)
        self._add_child(self.CHILD_PREPEND, row)

    def append_child(self, station_id: int):
        row = self._child_model.get(station_id)
        self._add_child(self.CHILD_APPEND, row)

    def model(self):
        return self._get_sql_manager().factor(MapLine)

    def child_model(self):
        return self._child_model

    def _add_child(self, mode: int, row: dict):
        item = MapStationItem(self, row)
        self._children[f'id_{row["station_id"]}'] = item
        if mode is self.CHILD_APPEND:
            return self.appendRow(item)
        return self.insertRow(0, item)


class ImportStationItem(QStandardItem, ItemMixin):

    def __init__(self, parent: QStandardItem, station_row: dict):
        super().__init__(self.get_icon(self.type()), station_row['station_name'])
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(ImportStation)
        self._item_data = station_row

    def type(self) -> int:
        return self.ITEM_TYPE_STATION

    def type_root(self) -> int:
        return self._parent.type_root()

    def survey_id(self) -> int:
        return self._parent.survey_id()

    def line_id(self) -> int:
        return self._parent.line_id()

    def station_id(self) -> int:
        return self._item_data['station_id']

    def remove(self):
        self.parent().removeRow(self.row())

    def model(self):
        return self._child_model

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()


class ImportLineItem(QStandardItem, ItemMixin):

    def __init__(self, parent: QStandardItem, line_row: dict):
        super().__init__(self.get_icon(self.type()), line_row['line_name'])
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(ImportStation)
        self._item_data = line_row
        self._children = {}

        self.append_children()

    def type(self) -> int:
        return self.ITEM_TYPE_LINE

    def type_root(self) -> int:
        return self._parent.type_root()

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()

    def survey_id(self) -> int:
        return self._parent.survey_id()

    def line_id(self) -> int:
        return self._item_data['line_id']

    def update(self, name: str):
        self.setText(name)

    def remove(self):
        self.parent().removeRow(self.row())

    def update_children(self):
        self.removeRows(0, self.rowCount())
        self.append_children()

    def append_children(self):
        rows = self._child_model.get_all(self.line_id())
        for row in rows:
            self._add_child(self.CHILD_APPEND, row)

    def prepend_child(self, station_id: int):
        row = self._child_model.get(station_id)
        self._add_child(self.CHILD_PREPEND, row)

    def append_child(self, station_id: int):
        row = self._child_model.get(station_id)
        self._add_child(self.CHILD_APPEND, row)

    def model(self):
        return self._get_sql_manager().factor(ImportLine)

    def child_model(self):
        return self._child_model

    def _add_child(self, mode: int, row: dict):
        item = ImportStationItem(self, row)
        self._children[f'id_{row["station_id"]}'] = item
        if mode is self.CHILD_APPEND:
            return self.appendRow(item)
        return self.insertRow(0, item)


class ImportSurveyItem(QStandardItem, ItemMixin):

    def __init__(self, parent: QStandardItem, survey_row: dict):
        super().__init__(self.get_icon(self.type()), survey_row['survey_name'])
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(ImportLine)
        self._item_data = survey_row
        self._children = {}

        self.append_children()

    def type(self) -> int:
        return self.ITEM_TYPE_SURVEY

    def type_root(self) -> int:
        return self._parent.type_root()

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()

    def survey_id(self) -> int:
        return self._item_data['survey_id']

    def update(self, name: str):
        self.setText(name)

    def remove(self):
        self.parent().removeRow(self.row())

    def append_children(self):
        rows = self._child_model.get_all(self.survey_id())
        for row in rows:
            self._add_child(self.CHILD_APPEND, row)

    def update_children(self):
        self.removeRows(0, self.rowCount())
        self.append_children()

    def prepend_child(self, line_id: int):
        row = self._child_model.get(line_id)
        self._add_child(self.CHILD_PREPEND, row)

    def append_child(self, line_id: int):
        row = self._child_model.get(line_id)
        self._add_child(self.CHILD_APPEND, row)

    def model(self):
        return self._get_sql_manager().factor(ImportSurvey)

    def child_model(self):
        return self._child_model

    def _add_child(self, mode: int, row: dict):
        item = ImportLineItem(self, row)
        self._children[f'id_{row["line_id"]}'] = item
        if mode is self.CHILD_APPEND:
            return self.appendRow(item)
        return self.insertRow(0, item)


class ImportItem(QStandardItem, ItemMixin):

    def __init__(self, parent):
        super().__init__(self.get_icon(self.type()), "Import data")
        self._parent = parent
        self._child_model = self._get_sql_manager().factor(ImportSurvey)
        self.surveys = {}
        self.append_children()

    def type(self) -> int:
        return self.ITEM_TYPE_IMPORTS

    def type_root(self) -> int:
        return self.ITEM_TYPE_IMPORTS

    def append_children(self):
        survey_rows = self._child_model.get_all()
        for survey_row in survey_rows:
            self._add_child(self.CHILD_APPEND, survey_row)

    def update_children(self):
        self.removeRows(0, self.rowCount())
        self.append_children()

    def prepend_child(self, survey_id: int):
        survey_data = self._child_model.get(survey_id)
        self._add_child(self.CHILD_PREPEND, survey_data)

    def append_child(self, survey_id: int):
        survey_data = self._child_model.get(survey_id)
        self._add_child(self.CHILD_APPEND, survey_data)

    def delete_children(self):
        self.removeRows(0, self.rowCount())

    def model(self):
        return self.child_model()

    def child_model(self):
        return self._child_model

    def _add_child(self, mode: int, row: dict):
        item = ImportSurveyItem(self, row)
        self.surveys[f'id_{row["survey_id"]}'] = item
        if mode is self.CHILD_APPEND:
            return self.appendRow(item)
        return self.insertRow(0, item)

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()


class MapsItem(QStandardItem, ItemMixin):

    def __init__(self, parent):
        super().__init__(self.get_icon(self.type()), "Map data")
        self._parent = parent
        self._children = {}
        self._child_model = self._get_sql_manager().factor(MapLine)
        self.append_children()

    def type(self) -> int:
        return self.ITEM_TYPE_MAPS

    def type_root(self) -> int:
        return self.ITEM_TYPE_MAP

    def append_children(self):
        rows = self._child_model.get_all()
        for row in rows:
            self._add_child(self.CHILD_APPEND, row)

    def prepend_child(self, line_id: int):
        row = self._child_model.get(line_id)
        self._add_child(self.CHILD_PREPEND, row)

    def delete_children(self):
        self.removeRows(0, self.rowCount())

    def append_child(self, line_id: int):
        row = self._child_model.get(line_id)
        self._add_child(self.CHILD_APPEND, row)

    def model(self):
        return self.child_model()

    def child_model(self):
        return self._child_model

    def _add_child(self, mode: int, row: dict):
        item = MapLineItem(self, row)
        self._children[f'id_{row["line_id"]}'] = item
        if mode is self.CHILD_APPEND:
            return self.appendRow(item)
        return self.insertRow(0, item)

    def _get_sql_manager(self) -> SqlManager:
        return self._parent._get_sql_manager()


class ProxyModel(QStandardItemModel, ItemMixin):

    def __init__(self, sql_manager: SqlManager):
        super().__init__()
        self._sql_manager = sql_manager
        self._import_item = ImportItem(self)
        self._map_item = MapsItem(self)

        self.appendRow(self._import_item)
        self.appendRow(self._map_item)

    @Slot(dict)  # connected in MainApplicationWindow.__init__() as I don't have the parent here.
    def c_load_project(self):
        imp = self.import_item()
        mp = self.map_item()
        imp.delete_children()
        mp.delete_children()

        imp.append_children()
        mp.append_children()

    def import_item(self) -> ImportItem:
        return self._import_item

    def map_item(self) -> MapsItem:
        return self._map_item

    def _get_sql_manager(self) -> SqlManager:
        return self._sql_manager



