import json
from datetime import datetime

from PySide6.QtCore import QModelIndex, Qt, QSettings
from PySide6.QtSql import QSqlTableModel, QSqlQuery, QSqlRelationalTableModel, QSqlRelation, QSqlDatabase

from Config.Constants import SQL_TABLE_STATIONS, SQL_TABLE_SECTIONS, SQL_TABLE_SURVEYS, SQL_TABLE_CONTACTS, \
    SQL_TABLE_EXPLORERS, SQL_TABLE_SURVEYORS, SQL_DB_LOCATION, SQL_CONNECTION_NAME


class QueryMixin:

    def db_exec(self, sql):
        settings = QSettings()
        settings.setValue('SaveFile/is_changed', True)
        query = QSqlQuery(self.db)
        return query.exec_(sql)

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
        obj = QSqlQuery(self.db)
        obj.prepare(query)
        for value in params:
            obj.addBindValue(value)

        if obj.exec_() is False:
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
        obj = QSqlQuery(self.db)
        obj.prepare(query)

        for value in params:
            obj.addBindValue(value)

        obj.exec_()
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

        obj = QSqlQuery(self.db)
        obj.prepare(sql)

        for param in params:
            obj.addBindValue(param)

        obj.exec_()
        rows = []
        while obj.next():
            row = {}
            for index in range(0, obj.record().count()):
                row[obj.record().fieldName(index)] = obj.value(index)
            rows.append(row)
        return rows

    def __init__(self, db):
        self.db = db


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
            self.db.setDatabaseName(SQL_DB_LOCATION)
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
                survey_datetime TEXT,
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

    def insert_survey(self, device_name: str) -> int:
        self.select()
        # do not set break-points here, you will start inserting multiple records per break-point.
        record = self.record()
        now = datetime.now()
        record.setValue('survey_id', None)
        record.setValue('device_name', device_name)
        record.setValue('survey_datetime', now.timestamp())
        record.setValue('survey_name', now.strftime('%c'))
        record.setValue('survey_comment', '')
        # -1 is set to indicate that it will be added to the last row
        if self.insertRecord(-1, record):
            self.submitAll()
            last_insert_id = self.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert survey')

    def update_survey(self, values: dict, survey_id: int) -> int:
        return self.db_update(SQL_TABLE_SURVEYS, values, 'survey_id=?', [survey_id])

    def delete_survey(self, survey_id: int) -> int:
        a = self.db_delete(SQL_TABLE_STATIONS, 'survey_id=?', [survey_id])
        b = self.db_delete(SQL_TABLE_SECTIONS, 'survey_id=?', [survey_id])
        c = self.db_delete(SQL_TABLE_SURVEYS, 'survey_id=?', [survey_id])
        return a + b + c

    def dump_table(self):
        return self.db_fetch(f"SELECT * FROM {SQL_TABLE_SURVEYS} ORDER BY survey_id ASC")

    def load_table(self, table_data: list):
        if len(table_data) == 0:
            return 0
        return self.db_insert_bulk(SQL_TABLE_SURVEYS, table_data)

    def __init__(self, db):
        QueryMixin.__init__(self, db=db)
        QSqlTableModel.__init__(self, db=db)
        self.setTable(SQL_TABLE_SURVEYS)
        self.setEditStrategy(self.OnManualSubmit)


class Section(QueryMixin, QSqlTableModel):

    def create_database_tables(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_SECTIONS} (
                section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                section_reference_id INTEGER,
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

    def insert_section(self, survey_id: int, section_reference_id: int, device_properties: dict) -> int:
        self.select()
        # do not set breakstations here, you will start inserting multiple records per breakstation.
        record = self.record()
        now = datetime.now()
        record.setValue('section_id', None)
        record.setValue('survey_id', survey_id)
        record.setValue('section_reference_id', section_reference_id)
        record.setValue('device_properties', json.dumps(device_properties))
        record.setValue('section_name', f'Section {section_reference_id}')
        record.setValue('section_comment', '')
        # -1 is set to indicate that it will be added to the last row
        if self.insertRecord(-1, record):
            self.submitAll()
            last_insert_id = self.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert section')

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
        flags = Qt.NoItemFlags
        if index.column() in [2, 3]:
            return flags

        return flags | Qt.ItemIsEditable | Qt.ItemIsEnabled


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
                temperature REAL,
                azimuth_out REAL,
                azimuth_out_avg REAL,
                length_out REAL,
                station_comment TEXT
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
        self.select()
        # do not set breakstations here, you will start inserting multiple records per breakstation.
        record = self.record()
        now = datetime.now()
        record.setValue('station_id', None)
        record.setValue('section_id', section_id)
        record.setValue('survey_id', survey_id)
        record.setValue('section_reference_id', section_reference_id)
        record.setValue('station_reference_id', station_reference_id)
        record.setValue('length_in', length_in)
        record.setValue('length_out', length_out)
        record.setValue('azimuth_in', azimuth_in)
        record.setValue('azimuth_out', azimuth_out)
        record.setValue('azimuth_out_avg', azimuth_out_avg)
        record.setValue('depth', depth)
        record.setValue('station_properties', json.dumps(station_properties))
        record.setValue('station_name', station_name)

        # -1 is set to indicate that it will be added to the last row
        if self.insertRecord(-1, record):
            self.submitAll()
            last_insert_id = self.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert station')


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
