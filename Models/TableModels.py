import json
import logging
from datetime import datetime

from PySide6.QtCore import QModelIndex, Qt, QSettings, QDateTime
from PySide6.QtSql import QSqlTableModel, QSqlQuery, QSqlRelationalTableModel, QSqlRelation, QSqlDatabase

from Config.Constants import SQL_TABLE_IMPORT_STATIONS, SQL_TABLE_IMPORT_LINES, SQL_TABLE_IMPORT_SURVEYS, \
    SQL_TABLE_CONTACTS, \
    SQL_TABLE_EXPLORERS, SQL_TABLE_SURVEYORS, SQL_DB_LOCATION, SQL_CONNECTION_NAME, DEBUG, SQL_TABLE_MAP_LINES, \
    SQL_TABLE_MAP_STATIONS, SQL_TABLE_PROJECT_SETTINGS, SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT
from Gui.Delegates.FormElements import CommentEditor, DateTimeEditor, DropDown
from Utils.Settings import Preferences


class QueryMixin:

    def db_exec(self, sql: str, params: list = []):
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        obj = QSqlQuery(self.db)
        status = obj.prepare(sql)
        if status is False:
            self._log.error(f'db_exec prepare failed: {obj.lastError()} for sql: {sql}')

        for value in params:
            obj.addBindValue(value)

        obj.exec_()
        err = obj.lastError().text()
        if len(err) > 0:
            self._log.error(f'db_exec exec error: {err} for sql: {sql}')
        return obj

    def db_insert(self, table_name: str, values: dict) -> int:
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        col_names = ', '.join(values.keys())
        placeholders = ', '.join('?' for x in values.values())
        query = 'INSERT INTO {} ({})VALUES({})'.format(table_name, col_names, placeholders)
        obj = QSqlQuery(self.db)
        obj.prepare(query)

        for value in values.values():
            obj.addBindValue(value)

        if obj.exec_() is False:
            raise SyntaxError(f'Sql insert query failed! {query}')
        insert_id = obj.lastInsertId()
        obj.clear()
        return insert_id

    def db_insert_bulk(self, table_name: str, values: list, max_batch_size: int=10, start_at: int=0) -> int:
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        col_names = ', '.join(values[0].keys())
        new_start_at = 0
        placeholders = []
        params = []
        for index, row in enumerate(values[start_at::]):
            placeholders.append('({})'.format(', '.join('?' for x in row.values())))
            params.extend(row.values())
            if index == max_batch_size - 1:
                new_start_at = start_at + index + 1
                break

        placeholder = ', '.join(placeholders)
        query = f'INSERT INTO {table_name} ({col_names})VALUES {placeholder}'
        obj = self.db_exec(query, params)

        if obj is False:
            self._log.error(f'Sql bulk insert query failed! {obj.lastError()}')
            raise SyntaxError('Sql bulk insert query failed!')
        row_count = obj.numRowsAffected()
        if new_start_at > 0:
            row_count = row_count + self.db_insert_bulk(table_name, values, max_batch_size, new_start_at)
        return row_count

    def db_update(self, table_name: str, values: dict, where_str: str, params: list = []) -> int:
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        update_cols = ', '.join('{}=?'.format(x) for x in values.keys())
        query = 'UPDATE {} SET {} WHERE {}'.format(table_name, update_cols, where_str)
        obj = QSqlQuery(self.db)
        obj.prepare(query)

        for value in values.values():
            obj.addBindValue(value)
        for value in params:
            obj.addBindValue(value)

        obj.exec_()
        return obj.numRowsAffected()

    def db_delete(self, table_name: str, where_str: str = None, params: list = []) -> int:
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        query = f'DELETE FROM {table_name}'
        if where_str is not None:
            query = f'{query} WHERE {where_str}'
        obj = self.db_exec(query, params)
        return obj.numRowsAffected()

    def db_get(self, table_name, where_str=None, params=[]) -> dict:
        if type(params) is not list:
            params = [params]

        query = f"SELECT * FROM {table_name}"
        if where_str is not None:
            query = f"{query} WHERE {where_str}"

        obj = QSqlQuery(self.db)
        obj.prepare(query)

        for param in params:
            obj.addBindValue(param)

        obj.exec_()
        if obj.first() is False:
            return None
        row = {}
        for index in range(0, obj.record().count()):
            row[obj.record().fieldName(index)] = obj.value(index)

        return row

    def db_fetch(self, sql, params=[]):
        if type(params) is not list:
            params = [params]

        obj = self.db_exec(sql, params)
        rows = []
        while obj.next():
            row = {}
            for index in range(0, obj.record().count()):
                row[obj.record().fieldName(index)] = obj.value(index)
            rows.append(row)
        return rows

    def __init__(self, db):
        self.db = db
        self._log = logging.getLogger(__name__)


class SqlManager:

    def drop_db(self):
        self.drop_tables()
        self.close_connection()
        QSqlDatabase.removeDatabase(self.connection_name)

    def factor(self, object_name):
        return object_name(self.db)

    def create_tables(self):
        self.factor(ProjectSettings).create_database_tables()
        self.factor(ImportSurvey).create_database_tables()
        self.factor(ImportLine).create_database_tables()
        self.factor(ImportStation).create_database_tables()
        self.factor(MapLine).create_database_tables()
        self.factor(MapStation).create_database_tables()
        self.factor(Contact).create_database_tables()
        self.factor(Surveyor).create_database_tables()
        self.factor(Explorer).create_database_tables()

    def drop_tables(self):
        self.factor(ProjectSettings).drop_database_tables()
        self.factor(ImportSurvey).drop_database_tables()
        self.factor(ImportLine).drop_database_tables()
        self.factor(ImportStation).drop_database_tables()
        self.factor(MapLine).drop_database_tables()
        self.factor(MapStation).drop_database_tables()
        self.factor(Contact).drop_database_tables()
        self.factor(Surveyor).drop_database_tables()
        self.factor(Explorer).drop_database_tables()

    def dump_tables(self):
        return {
            SQL_TABLE_PROJECT_SETTINGS: self.factor(ProjectSettings).dump_table(),
            SQL_TABLE_IMPORT_SURVEYS: self.factor(ImportSurvey).dump_table(),
            SQL_TABLE_IMPORT_LINES: self.factor(ImportLine).dump_table(),
            SQL_TABLE_IMPORT_STATIONS: self.factor(ImportStation).dump_table(),
            SQL_TABLE_MAP_LINES: self.factor(MapLine).dump_table(),
            SQL_TABLE_MAP_STATIONS: self.factor(MapStation).dump_table(),
            SQL_TABLE_CONTACTS: self.factor(Contact).dump_table(),
            SQL_TABLE_SURVEYORS: self.factor(Surveyor).dump_table(),
            SQL_TABLE_EXPLORERS: self.factor(Explorer).dump_table()
        }

    def load_table_data(self, data: dict) -> int:
        c = 0
        c = c + self.factor(ProjectSettings).load_table(data[SQL_TABLE_PROJECT_SETTINGS])
        c = c + self.factor(ImportSurvey).load_table(data[SQL_TABLE_IMPORT_SURVEYS])
        c = c + self.factor(ImportLine).load_table(data[SQL_TABLE_IMPORT_LINES])
        c = c + self.factor(ImportStation).load_table(data[SQL_TABLE_IMPORT_STATIONS])
        c = c + self.factor(MapLine).load_table(data[SQL_TABLE_MAP_LINES])
        c = c + self.factor(MapStation).load_table(data[SQL_TABLE_MAP_STATIONS])
        c = c + self.factor(Contact).load_table(data[SQL_TABLE_CONTACTS])
        c = c + self.factor(Explorer).load_table(data[SQL_TABLE_EXPLORERS])
        c = c + self.factor(Surveyor).load_table(data[SQL_TABLE_SURVEYORS])
        return c

    def close_connection(self):
        if self.db is not None:
            self.db.close()
            self.db = None
            if QSqlDatabase.contains(self.connection_name):
                QSqlDatabase.removeDatabase(self.connection_name)

    def __init__(self, connection_name=SQL_CONNECTION_NAME):
        self.connection_name = connection_name
        if QSqlDatabase.contains(connection_name) is False:
            self.db = QSqlDatabase.addDatabase('QSQLITE', connection_name)
            self.db.setDatabaseName(Preferences.get('sql_db_location', SQL_DB_LOCATION, str))
        else:
            self.db = QSqlDatabase.database(connection_name)

        if not self.db.open():
            raise ConnectionError(f"Database Error: {self.db.lastError()}")

    def flush_db(self):
        self.drop_tables()
        self.create_tables()


class ProjectSettings(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
               CREATE TABLE IF NOT EXISTS {SQL_TABLE_PROJECT_SETTINGS} (
                   project_id INTEGER PRIMARY KEY AUTOINCREMENT,
                   project_name TEXT,
                   latitude FLOAT,
                   longitude FLOAT,
                   date_created FLOAT,
                   last_update FLOAT
               )
           """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                       DROP TABLE IF EXISTS {SQL_TABLE_PROJECT_SETTINGS}
                   """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_PROJECT_SETTINGS} ORDER BY project_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_PROJECT_SETTINGS, table_data)

    def insert(self, project_name, latitude, longitude):
        props = {
            'project_name': project_name,
            'latitude': latitude,
            'longitude': longitude,
            'date_created': datetime.now().timestamp(),
            'last_update': datetime.now().timestamp()
        }

        self.db_insert(SQL_TABLE_PROJECT_SETTINGS, props)

    def get(self):
        return self.db_get(SQL_TABLE_PROJECT_SETTINGS)

    def update(self):
        self.db_update(SQL_TABLE_PROJECT_SETTINGS, {'last_update': datetime.timestamp()})


class ImportSurvey(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_IMPORT_SURVEYS} (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_name TEXT,
                survey_datetime INTEGER,
                device_name TEXT,
                survey_comment TEXT,
                device_properties TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_IMPORT_SURVEYS}
                """
        self.db_exec(query)

    def get_all(self) -> list:
        return self.db_fetch(f'SELECT survey_id, survey_name, device_name FROM {SQL_TABLE_IMPORT_SURVEYS} ORDER BY survey_id DESC', [])

    def get(self, survey_id) -> dict:
        return self.db_get(SQL_TABLE_IMPORT_SURVEYS, 'survey_id=?', [survey_id])

    def insert(self, device_name: str, device_properties: dict = {}) -> int:

        now = datetime.now()
        data = {
            'device_name': device_name,
            'device_properties': json.dumps(device_properties),
            'survey_datetime': now.timestamp(),
            'survey_name': f'{device_name} {now.month}-{now.day}',
            'survey_comment': ''
        }

        return self.db_insert(SQL_TABLE_IMPORT_SURVEYS, data)

    def update(self, values: dict, survey_id: int) -> int:
        return self.db_update(SQL_TABLE_IMPORT_SURVEYS, values, 'survey_id=?', [survey_id])

    def flush(self):
        a = self.db_delete(SQL_TABLE_IMPORT_STATIONS)
        b = self.db_delete(SQL_TABLE_IMPORT_LINES)
        c = self.db_delete(SQL_TABLE_IMPORT_SURVEYS)
        return a + b + c

    def delete(self, survey_id: int) -> int:
        a = self.db_delete(SQL_TABLE_IMPORT_STATIONS, 'survey_id=?', [survey_id])
        b = self.db_delete(SQL_TABLE_IMPORT_LINES, 'survey_id=?', [survey_id])
        c = self.db_delete(SQL_TABLE_IMPORT_SURVEYS, 'survey_id=?', [survey_id])
        return a + b + c

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_IMPORT_SURVEYS} ORDER BY survey_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_IMPORT_SURVEYS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_IMPORT_SURVEYS)
        self.setEditStrategy(self.OnManualSubmit)

        self.setHeaderData(0, Qt.Horizontal, "Survey id")
        self.setHeaderData(1, Qt.Horizontal, "Survey name")
        self.setHeaderData(2, Qt.Horizontal, "Date & time")
        self.setHeaderData(3, Qt.Horizontal, "Device name")
        self.setHeaderData(4, Qt.Horizontal, "Survey comment")
        self.setHeaderData(5, Qt.Horizontal, "Device properties")

    def set_column_widths(self, view):
        if Preferences.debug() is False:
            view.setColumnHidden(0, True)
            view.setColumnHidden(5, True)

        view.setColumnWidth(0, 50)
        view.setColumnWidth(1, 140)
        view.setColumnWidth(2, 160)
        view.setColumnWidth(3, 100)
        view.setColumnWidth(4, 200)

        editor = CommentEditor(view.parent())
        view.setItemDelegateForColumn(4, editor)
        date = DateTimeEditor(view.parent())
        view.setItemDelegateForColumn(2, date)
        return view

    def flags(self, index: QModelIndex):
        # this also affects the insert of a record.
        if index.column() in [0, 5]:
            return Qt.NoItemFlags  # both the id and device properties are un-editable.

        return Qt.ItemIsEditable | Qt.ItemIsEnabled

    def data(self, index, role):
        if role == Qt.TextAlignmentRole:
            if index.column() in (1, 2, 3,):
                return Qt.AlignCenter

        return super().data(index, role)


class ImportLine(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_IMPORT_LINES} (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                line_reference_id INTEGER,
                line_name TEXT,
                direction TEXT,
                line_comment TEXT,
                device_properties TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_IMPORT_LINES}
                """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_IMPORT_LINES} ORDER BY line_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_IMPORT_LINES, table_data)


    def get(self, line_id) -> dict:
        return self.db_get(SQL_TABLE_IMPORT_LINES, 'line_id=?', [line_id])

    def get_all(self, survey_id: int, all_columns: bool = False) -> list:
        if all_columns:
            select = '*'
        else:
            select = 'line_id, line_name'
        return self.db_fetch(f'SELECT {select} FROM {SQL_TABLE_IMPORT_LINES} WHERE survey_id=? ORDER BY line_id ASC', [survey_id])

    def insert(self, survey_id: int, line_reference_id: int, direction: str, device_properties: dict) -> int:
        data = {
            'survey_id': survey_id,
            'line_reference_id': line_reference_id,
            'direction': direction,
            'device_properties': json.dumps(device_properties),
            'line_name': f'Line {line_reference_id}',
            'line_comment': ''
        }
        return self.db_insert(SQL_TABLE_IMPORT_LINES, data)

    def update(self, values: dict, line_id: int) -> int:
        return self.db_update(SQL_TABLE_IMPORT_LINES, values, 'line_id=?', [line_id])

    def delete(self, line_id: int) -> int:
        a = self.db_delete(SQL_TABLE_IMPORT_STATIONS, 'line_id=?', [line_id])
        b = self.db_delete(SQL_TABLE_IMPORT_LINES, 'line_id=?', [line_id])
        return a + b

    def flush_empty(self, survey_id):
        q = f"""
            DELETE FROM {SQL_TABLE_IMPORT_LINES} WHERE line_id IN (
                SELECT a.line_id
                    FROM {SQL_TABLE_IMPORT_LINES} AS a
                         LEFT JOIN {SQL_TABLE_IMPORT_STATIONS} AS b ON a.line_id = b.line_id
                WHERE a.survey_id = ?
                  AND station_id IS NULL
            )
        """
        logging.getLogger(__name__).info(f'removing empty lines for survey_id={survey_id}')
        res = self.db_exec(q, [survey_id])
        return res.numRowsAffected()

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_IMPORT_LINES)
        self.setEditStrategy(self.OnManualSubmit)

        self.setHeaderData(0, Qt.Horizontal, "Survey id")
        self.setHeaderData(1, Qt.Horizontal, "Line id")
        self.setHeaderData(2, Qt.Horizontal, "ID")
        self.setHeaderData(3, Qt.Horizontal, "Line name")
        self.setHeaderData(4, Qt.Horizontal, "Direction")
        self.setHeaderData(5, Qt.Horizontal, "Comment")
        self.setHeaderData(6, Qt.Horizontal, "Device properties")

    def set_column_widths(self, view):
        if Preferences.debug() is False:
            view.setColumnHidden(0, True)
            view.setColumnHidden(1, True)
            view.setColumnHidden(6, True)

        view.setColumnWidth(0, 20)
        view.setColumnWidth(1, 100)
        view.setColumnWidth(2, 110)
        view.setColumnWidth(3, 100)
        view.setColumnWidth(4, 120)
        view.setColumnWidth(5, 140)

        drop = DropDown(self)
        drop.setOptions((SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT))
        view.setItemDelegateForColumn(4, drop)

        comment = CommentEditor(self)
        view.setItemDelegateForColumn(5, comment)

    def flags(self, index: QModelIndex):
        if index.column() in (0,1, 6):
            return Qt.NoItemFlags

        return Qt.ItemIsEditable | Qt.ItemIsEnabled

    def data(self, index, role):
        data = super().data(index, role)
        if role == Qt.TextAlignmentRole:
            if index.column() in (2, 3, 4,):
                return Qt.AlignCenter

        return data


class ImportStation(QueryMixin, QSqlTableModel):


    def create_database_tables(self):
        # reference_id is the "id" as provider by the Mnemo.
        # so it is a local reference id only unique to the section itself.
        query = f"""
                    CREATE TABLE IF NOT EXISTS {SQL_TABLE_IMPORT_STATIONS} (
                        station_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        line_id INTEGER,
                        survey_id INTEGER,
                        line_reference_id INTEGER,
                        station_reference_id INTEGER,
                        station_name TEXT,
                        length_in REAL,
                        azimuth_in REAL,
                        depth REAL,
                        azimuth_out REAL,
                        azimuth_out_avg REAL,
                        length_out REAL,
                        longitude REAL DEFAULT NULL,
                        latitude REAL DEFAULT NULL,
                        station_comment TEXT,
                        device_properties TEXT
                    )
                """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_IMPORT_STATIONS}
                """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_IMPORT_STATIONS} ORDER BY station_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_IMPORT_STATIONS, table_data)

    def insert(self,
               survey_id: int,
               line_id: int,
               line_reference_id: int,
               station_reference_id: int,
               length_in: float,
               length_out: float,
               azimuth_in: float,
               azimuth_out: float,
               azimuth_out_avg: float,
               depth: float,
               station_properties: dict = {},
               station_name: str = ''
               ) -> int:
        data = {
            'station_id': None,
            'line_id': line_id,
            'survey_id': survey_id,
            'line_reference_id': line_reference_id,
            'station_reference_id': station_reference_id,
            'length_in': length_in,
            'length_out': length_out,
            'azimuth_in': azimuth_in,
            'azimuth_out': azimuth_out,
            'azimuth_out_avg': azimuth_out_avg,
            'depth': depth,
            'device_properties': json.dumps(station_properties),
            'station_name': station_name
        }

        return self.db_insert(SQL_TABLE_IMPORT_STATIONS, data)

    def update(self, values: dict, station_id: int) -> int:
        return self.db_update(SQL_TABLE_IMPORT_STATIONS, values, 'station_id=?', [station_id])

    def delete(self, station_id: int) -> int:
        return self.db_delete(SQL_TABLE_IMPORT_STATIONS, 'station_id=?', [station_id])



    def get(self, station_id) -> dict:
        return self.db_get(SQL_TABLE_IMPORT_STATIONS, 'station_id=?', [station_id])

    def get_all(self, line_id) -> dict:
        return self.db_fetch(f'SELECT * FROM {SQL_TABLE_IMPORT_STATIONS} WHERE line_id=? ORDER BY station_id ASC', [line_id])

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_IMPORT_STATIONS)
        self.setEditStrategy(self.OnManualSubmit)

        self.setHeaderData(0, Qt.Horizontal, "Station id")
        self.setHeaderData(1, Qt.Horizontal, "Line id")
        self.setHeaderData(2, Qt.Horizontal, "Survey id")
        self.setHeaderData(3, Qt.Horizontal, "ID")
        self.setHeaderData(4, Qt.Horizontal, "Device line reference id")
        self.setHeaderData(5, Qt.Horizontal, "Station name")
        self.setHeaderData(6, Qt.Horizontal, "Length in")
        self.setHeaderData(7, Qt.Horizontal, "Azimuth in")
        self.setHeaderData(8, Qt.Horizontal, "Depth")
        self.setHeaderData(9, Qt.Horizontal, "Azimuth out")
        self.setHeaderData(10, Qt.Horizontal, "Azimuth corrected")
        self.setHeaderData(11, Qt.Horizontal, "Length out")
        self.setHeaderData(13, Qt.Horizontal, "Latitude")
        self.setHeaderData(14, Qt.Horizontal, "Longitude")
        self.setHeaderData(12, Qt.Horizontal, "Station Comment")
        self.setHeaderData(15, Qt.Horizontal, "Device properties")

    def set_column_widths(self, view):
        view.setColumnHidden(1, True)
        view.setColumnHidden(2, True)
        view.setColumnHidden(4, True)

        if Preferences.debug() is False:
            view.setColumnHidden(0, True)
            view.setColumnHidden(15, True)


        view.setColumnWidth(0, 60)
        view.setColumnWidth(1, 70)
        view.setColumnWidth(2, 110)
        view.setColumnWidth(3, 100)
        view.setColumnWidth(4, 120)
        view.setColumnWidth(5, 140)
        view.setColumnWidth(6, 140)
        view.setColumnWidth(7, 140)
        view.setColumnWidth(8, 140)
        view.setColumnWidth(9, 140)
        view.setColumnWidth(10, 140)
        view.setColumnWidth(11, 140)
        view.setColumnWidth(12, 140)
        view.horizontalHeader().setStretchLastSection(True)



    # def flags(self, index: QModelIndex):
    #     if index.column() in (0, 1, 2, 3, 4, 13, 7,9):
    #         return Qt.NoItemFlags
    #
    #     return Qt.ItemIsEditable | Qt.ItemIsEnabled
    #
    # def data(self, index, role):
    #     data = super().data(index, role)
    #     if role == Qt.TextAlignmentRole:
    #         if index.column() in (0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11,):
    #             return Qt.AlignCenter
    #
    #     return data


class MapLine(QueryMixin, QSqlTableModel):
    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_MAP_LINES} (
                line_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_reference_id INTEGER,
                direction TEXT,
                device_properties TEXT,
                line_name TEXT,
                line_comment TEXT,
                line_color TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_MAP_LINES}
                """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_MAP_LINES} ORDER BY line_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_MAP_LINES, table_data)

    def get(self, line_id) -> dict:
        return self.db_get(SQL_TABLE_MAP_LINES, 'line_id=?', [line_id])

    def get_all(self) -> list:
        return self.db_fetch(f'SELECT line_id, line_name FROM {SQL_TABLE_MAP_LINES} ORDER BY line_id ASC')

    def insert(self, line_reference_id: int, direction: str, device_properties: dict) -> int:
        data = {
            'line_reference_id': line_reference_id,
            'direction': direction,
            'device_properties': json.dumps(device_properties),
            'line_name': f'Line {line_reference_id}',
            'line_comment': ''
        }
        return self.db_insert(SQL_TABLE_MAP_LINES, data)

    def update(self, values: dict, line_id: int) -> int:
        return self.db_update(SQL_TABLE_MAP_LINES, values, 'line_id=?', [line_id])

    def delete(self, line_id: int) -> int:
        a = self.db_delete(SQL_TABLE_MAP_STATIONS, 'line_id=?', [line_id])
        b = self.db_delete(SQL_TABLE_MAP_LINES, 'line_id=?', [line_id])
        return a + b


class MapStation(QueryMixin, QSqlTableModel):
    def create_database_tables(self):
        """
            @todo: fields to add + description

            year                  : the year of when the survey was done, used to correctly calculate the magnetic variation of the earth.
            longitude             : We use the lat/long coordinate system as a grid unit, this makes using googlemaps and bing easier
            latitude              : Same story
            merge_with_station_id : the station that it should connect to
            merge_with_line_id    : the line_id that it connects with, we can probably use this for threading later on?

        :return:
        """
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_MAP_STATIONS} (
                station_id INTEGER PRIMARY KEY AUTOINCREMENT,
                line_id INTEGER,
                station_reference_id INTEGER,
                line_reference_id INTEGER,
                station_name TEXT,
                length_in REAL,
                azimuth_in REAL,
                depth REAL,
                azimuth_out REAL,
                azimuth_out_avg REAL,
                length_out REAL,
                station_comment TEXT,
                device_properties TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_MAP_STATIONS}
                """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_MAP_STATIONS} ORDER BY station_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_MAP_STATIONS, table_data)

    def insert(self,
               survey_id: int,
               line_id: int,
               line_reference_id: int,
               station_reference_id: int,
               length_in: float,
               length_out: float,
               azimuth_in: float,
               azimuth_out: float,
               azimuth_out_avg: float,
               depth: float,
               station_properties: dict = {},
               station_name: str = ''
               ) -> int:
        data = {
            'station_id': None,
            'line_id': line_id,
            'survey_id': survey_id,
            'line_reference_id': line_reference_id,
            'station_reference_id': station_reference_id,
            'length_in': length_in,
            'length_out': length_out,
            'azimuth_in': azimuth_in,
            'azimuth_out': azimuth_out,
            'azimuth_out_avg': azimuth_out_avg,
            'depth': depth,
            'device_properties': json.dumps(station_properties),
            'station_name': station_name
        }

        return self.db_insert(SQL_TABLE_MAP_STATIONS, data)

    def update(self, values: dict, station_id: int) -> int:
        return self.db_update(SQL_TABLE_MAP_STATIONS, values, 'station_id=?', [station_id])

    def delete(self, station_id: int) -> int:
        return self.db_delete(SQL_TABLE_MAP_STATIONS, 'station_id=?', [station_id])

    def get(self, station_id) -> dict:
        return self.db_get(SQL_TABLE_MAP_STATIONS, 'station_id=?', [station_id])

    def get_all(self, line_id) -> dict:
        return self.db_fetch(f'SELECT * FROM {SQL_TABLE_MAP_STATIONS} WHERE line_id=? ORDER BY station_id ASC', [line_id])


class Contact(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_CONTACTS} (
                       contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT
                   )
               """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_CONTACTS}
                """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_CONTACTS} ORDER BY contact_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_CONTACTS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_CONTACTS)


class Explorer(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_EXPLORERS} (
                       explorer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                       DROP TABLE IF EXISTS {SQL_TABLE_EXPLORERS}
                   """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_EXPLORERS} ORDER BY explorer_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_EXPLORERS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_EXPLORERS)


class Surveyor(QueryMixin, QSqlRelationalTableModel):

    def create_database_tables(self):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_SURVEYORS} (
                       surveyor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                       DROP TABLE IF EXISTS {SQL_TABLE_SURVEYORS}
                   """
        self.db_exec(query)

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_SURVEYORS} ORDER BY surveyor_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_SURVEYORS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlRelationalTableModel.__init__(self, db=db)
        self.setRelation(1, QSqlRelation(SQL_TABLE_IMPORT_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))
