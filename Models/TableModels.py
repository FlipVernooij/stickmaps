import json
import logging
from datetime import datetime

from PySide6.QtCore import QModelIndex, Qt, QSettings, QDateTime
from PySide6.QtSql import QSqlTableModel, QSqlQuery, QSqlRelationalTableModel, QSqlRelation, QSqlDatabase

from Config.Constants import SQL_TABLE_STATIONS, SQL_TABLE_SECTIONS, SQL_TABLE_SURVEYS, SQL_TABLE_CONTACTS, \
    SQL_TABLE_EXPLORERS, SQL_TABLE_SURVEYORS, SQL_DB_LOCATION, SQL_CONNECTION_NAME, DEBUG
from Utils.Settings import Preferences


class QueryMixin:

    def db_exec(self, sql: str, params: list = []):
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        obj = QSqlQuery(self.db)
        status = obj.prepare(sql)
        if status is False:
            self._log.error(f'db_exec prepare failed: {obj.lastError()}')

        for value in params:
            obj.addBindValue(value)

        obj.exec_()
        err = obj.lastError().text()
        if len(err) > 0:
            self._log.error(f'db_exec exec error: {err}')
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
            raise SyntaxError('Sql insert query failed!')
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

    def db_delete(self, table_name: str, where_str: str, params: list = []) -> int:
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        query = f'DELETE FROM {table_name} WHERE {where_str}'
        obj = self.db_exec(query, params)
        return obj.numRowsAffected()

    def db_get(self, table_name, where_str, params) -> dict:
        if type(params) is not list:
            params = [params]

        query = f"SELECT * FROM {table_name} WHERE {where_str}"
        obj = QSqlQuery(self.db)
        obj.prepare(query)

        for param in params:
            obj.addBindValue(param)

        obj.exec_()
        # Doesn't work in sqlite
        # if obj.size() != 1:
        #     raise ValueError('Sqlite::get() can only return one row')

        obj.first()
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
        self.factor(Survey).create_database_tables()
        self.factor(Section).create_database_tables()
        self.factor(Station).create_database_tables()
        self.factor(Contact).create_database_tables()
        self.factor(Surveyor).create_database_tables()
        self.factor(Explorer).create_database_tables()

    def drop_tables(self):
        self.factor(Survey).drop_database_tables()
        self.factor(Section).drop_database_tables()
        self.factor(Station).drop_database_tables()
        self.factor(Contact).drop_database_tables()
        self.factor(Surveyor).drop_database_tables()
        self.factor(Explorer).drop_database_tables()

    def dump_tables(self):
        return {
            SQL_TABLE_SURVEYS: self.factor(Survey).dump_table(),
            SQL_TABLE_SECTIONS: self.factor(Section).dump_table(),
            SQL_TABLE_STATIONS: self.factor(Station).dump_table(),
            SQL_TABLE_CONTACTS: self.factor(Contact).dump_table(),
            SQL_TABLE_SURVEYORS: self.factor(Surveyor).dump_table(),
            SQL_TABLE_EXPLORERS: self.factor(Explorer).dump_table()
        }

    def load_table_data(self, data: dict) -> int:
        c = 0
        c = c + self.factor(Survey).load_table(data[SQL_TABLE_SURVEYS])
        c = c + self.factor(Section).load_table(data[SQL_TABLE_SECTIONS])
        c = c + self.factor(Station).load_table(data[SQL_TABLE_STATIONS])
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


class Survey(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = """
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                device_properties TEXT,
                survey_datetime INTEGER,
                survey_name TEXT,
                survey_comment TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_SURVEYS}
                """
        self.db_exec(query)

    def get_survey(self, survey_id) -> dict:
        return self.db_get(SQL_TABLE_SURVEYS, 'survey_id=?', [survey_id])

    def insert_survey(self, device_name: str, device_properties: dict = {}) -> int:

        now = datetime.now()
        data = {
            'device_name': device_name,
            'device_properties': json.dumps(device_properties),
            'survey_datetime': now.timestamp(),
            'survey_name': f'{device_name} {now.month}-{now.day}',
            'survey_comment': ''
        }

        return self.db_insert(SQL_TABLE_SURVEYS, data)

    def update_survey(self, values: dict, survey_id: int) -> int:
        return self.db_update(SQL_TABLE_SURVEYS, values, 'survey_id=?', [survey_id])

    def delete_survey(self, survey_id: int) -> int:
        a = self.db_delete(SQL_TABLE_STATIONS, 'survey_id=?', [survey_id])
        b = self.db_delete(SQL_TABLE_SECTIONS, 'survey_id=?', [survey_id])
        c = self.db_delete(SQL_TABLE_SURVEYS, 'survey_id=?', [survey_id])
        return a + b + c

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_SURVEYS} ORDER BY survey_id ASC")

    def remove_empty_sections(self, survey_id):
        q="""
            DELETE FROM sections WHERE section_id IN (
                SELECT a.section_id
                    FROM sections AS a
                         LEFT JOIN stations AS b ON a.section_id = b.section_id
                WHERE a.survey_id = ?
                  AND station_id IS NULL
            )
        """
        logging.getLogger(__name__).info(f'removing empty sections for survey_id={survey_id}')
        res = self.db_exec(q, [survey_id])
        return res.numRowsAffected()

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_SURVEYS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_SURVEYS)
        self.setEditStrategy(self.OnManualSubmit)

    def flags(self, index):
        # this also affects the insert of a record.
        if index.column() in [0, 2]:
            return Qt.NoItemFlags  # both the id and device properties are un-editable.
        return super().flags(index)

    def setData(self, index, value, role):

        if index.column() == 3:
            if role == Qt.EditRole:
                value = value.toSecsSinceEpoch()

        return super().setData(index, value, role)

    def data(self, index, role):
        data = super().data(index, role)
        if role == Qt.TextAlignmentRole:
            if index.column() in (0, 2, 3,):
                return Qt.AlignCenter
        if role == Qt.EditRole:
            if index.column() == 3:
                return QDateTime(datetime.fromtimestamp(data))
        if role == Qt.DisplayRole:
            if index.column() == 3:
                return datetime.fromtimestamp(data).ctime()
        return data


class Section(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_SECTIONS} (
                section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                section_reference_id INTEGER,
                direction TEXT,
                device_properties TEXT,
                section_name TEXT,
                section_comment TEXT
            )
        """
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_SECTIONS}
                """
        self.db_exec(query)

    def get_section(self, section_id) -> dict:
        return self.db_get(SQL_TABLE_SECTIONS, 'section_id=?', [section_id])

    def insert_section(self, survey_id: int, section_reference_id: int, direction: str, device_properties: dict) -> int:
        data = {
            'survey_id': survey_id,
            'section_reference_id': section_reference_id,
            'direction': direction,
            'device_properties': json.dumps(device_properties),
            'section_name': f'Section {section_reference_id}',
            'section_comment': ''
        }
        return self.db_insert(SQL_TABLE_SECTIONS, data)

    def update_section(self, values: dict, section_id: int) -> int:
        return self.db_update(SQL_TABLE_SECTIONS, values, 'section_id=?', [section_id])

    def delete_section(self, section_id: int) -> int:
        a = self.db_delete(SQL_TABLE_STATIONS, 'section_id=?', [section_id])
        b = self.db_delete(SQL_TABLE_SECTIONS, 'section_id=?', [section_id])
        return a + b

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_SECTIONS} ORDER BY section_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_SECTIONS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_SECTIONS)
        self.setEditStrategy(self.OnManualSubmit)

    def flags(self, index: QModelIndex):
        if index.column() in (0, 1, 2, 4,):
            return Qt.NoItemFlags

        return Qt.ItemIsEditable | Qt.ItemIsEnabled


    def data(self, index, role):
        data = super().data(index, role)
        if role == Qt.TextAlignmentRole:
            if index.column() in (1, 2, 3,):
                return Qt.AlignCenter
        # if role == Qt.EditRole:
        #     if index.column() == 3:
        #         # render an dropBox
        #         return
        return data


class Station(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_STATIONS} (
                station_id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                survey_id INTEGER,
                station_reference_id INTEGER,
                section_reference_id INTEGER,
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
        # reference_id is the "id" as provider by the Mnemo.
        # so it is a local reference id only unique to the section itself.
        self.db_exec(query)

    def drop_database_tables(self):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_STATIONS}
                """
        self.db_exec(query)

    def insert_station(self,
                       survey_id: int,
                       section_id: int,
                       section_reference_id: int,
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
                'section_id': section_id,
                'survey_id': survey_id,
                'section_reference_id': section_reference_id,
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

        return self.db_insert(SQL_TABLE_STATIONS, data)

    def update_station(self, values: dict, station_id: int) -> int:
        return self.db_update(SQL_TABLE_STATIONS, values, 'station_id=?', [station_id])

    def delete_station(self, station_id: int) -> int:
        return self.db_delete(SQL_TABLE_STATIONS, 'station_id=?', [station_id])

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_STATIONS} ORDER BY station_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_STATIONS, table_data)

    def get_station(self, station_id) -> dict:
        return self.db_get(SQL_TABLE_STATIONS, 'station_id=?', [station_id])

    def get_stations_for_section(self, section_id: int) -> list:
        return self.db_fetch(f'SELECT * FROM {SQL_TABLE_STATIONS} WHERE section_id=? ORDER BY station_id ASC', [section_id])

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_STATIONS)
        self.setEditStrategy(self.OnManualSubmit)

    def flags(self, index: QModelIndex):
        if index.column() in (0, 1, 2, 3, 4, 13, 7,9):
            return Qt.NoItemFlags

        return Qt.ItemIsEditable | Qt.ItemIsEnabled

    def data(self, index, role):
        data = super().data(index, role)
        if role == Qt.TextAlignmentRole:
            if index.column() in (0, 1, 2, 3, 4, 6, 7, 8, 9, 10, 11,):
                return Qt.AlignCenter

        return data

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
                       b_explorer_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
                       b_surveyor_id INTEGER PRIMARY KEY AUTOINCREMENT,
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
        self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))
