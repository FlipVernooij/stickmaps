import json
from datetime import datetime

from PySide6.QtCore import QModelIndex, Qt
from PySide6.QtSql import QSqlTableModel, QSqlQuery, QSqlRelationalTableModel, QSqlRelation, QSqlDatabase

from Config.Constants import SQL_TABLE_STATIONS, SQL_TABLE_SECTIONS, SQL_TABLE_SURVEYS, SQL_TABLE_CONTACTS, \
    SQL_TABLE_EXPLORERS, SQL_TABLE_SURVEYORS, SQL_DB_LOCATION


class QueryMixin:

    @classmethod
    def init_db(cls):
        db = QSqlDatabase.addDatabase('QSQLITE')
        db.setDatabaseName(SQL_DB_LOCATION)
        if not db.open():
            raise ConnectionError("Database Error: {}".format(db.lastError()))

    @classmethod
    def create_tables(cls):
        Survey.create_database_tables()
        Section.create_database_tables()
        Station.create_database_tables()
        Contact.create_database_tables()
        Surveyor.create_database_tables()
        Explorer.create_database_tables()

    @classmethod
    def drop_tables(cls):
        Contact.drop_database_tables()
        Explorer.drop_database_tables()
        Surveyor.drop_database_tables()
        Station.drop_database_tables()
        Section.drop_database_tables()
        Survey.drop_database_tables()


    @classmethod
    def dump_tables(cls):
        return {
            SQL_TABLE_SURVEYS: Survey.dump_table(),
            SQL_TABLE_SECTIONS: Section.dump_table(),
            SQL_TABLE_STATIONS: Station.dump_table(),
            SQL_TABLE_CONTACTS: Contact.dump_table(),
            SQL_TABLE_SURVEYORS: Surveyor.dump_table(),
            SQL_TABLE_EXPLORERS: Explorer.dump_table()
        }

    @classmethod
    def load_table_data(cls, data: dict) -> int:
        Survey.load_table(data[SQL_TABLE_SURVEYS])
        Section.load_table(data[SQL_TABLE_SECTIONS])
        Station.load_table(data[SQL_TABLE_STATIONS])
        Contact.load_table(data[SQL_TABLE_CONTACTS])
        Explorer.load_table(data[SQL_TABLE_EXPLORERS])
        Surveyor.load_table(data[SQL_TABLE_SURVEYORS])

    @classmethod
    def exec(cls, sql):
        query = QSqlQuery()
        return query.exec_(sql)

    @classmethod
    def insert(cls, table_name: str, values: dict) -> int:
        col_names = ', '.join(values.keys())
        placeholders = ', '.join('?' for x in values.values())
        query = 'INSERT INTO {} ({})VALUES({})'.format(table_name, col_names, placeholders)
        obj = QSqlQuery()
        obj.prepare(query)

        for value in values.values():
            obj.addBindValue(value)

        if obj.exec_() is False:
            raise SyntaxError('Sql insert query failed!')
        insert_id = obj.lastInsertId()
        obj.clear()
        return insert_id

    @classmethod
    def insert_bulk(cls, table_name: str, values: list, max_batch_size: int=100, start_at: int=0) -> int:
        col_names = ', '.join(values[0].keys())
        new_start_at = 0
        placeholders = []
        params = []
        for index, row in enumerate(values[start_at::]):
            if index > max_batch_size:
                new_start_at = index
                break
            placeholders.append('({})'.format(', '.join('?' for x in row.values())))
            params.extend(row.values())

        placeholder = ', '.join(placeholders)
        query = f'INSERT INTO {table_name} ({col_names})VALUES {placeholder}'
        obj = QSqlQuery()
        obj.prepare(query)
        for value in params:
            obj.addBindValue(value)

        if obj.exec_() is False:
            raise SyntaxError('Sql insert query failed!')
        row_count = obj.numRowsAffected()
        if new_start_at > 0:
            row_count = row_count + cls.insert_bulk(table_name, values, max_batch_size, new_start_at)
        return row_count



    @classmethod
    def update(cls, table_name: str, values: dict, where_str: str, params: list = []) -> int:
        update_cols = ', '.join('{}=?'.format(x) for x in values.keys())
        query = 'UPDATE {} SET {} WHERE {}'.format(table_name, update_cols, where_str)
        obj = QSqlQuery()
        obj.prepare(query)

        for value in values.values():
            obj.addBindValue(value)
        for value in params:
            obj.addBindValue(value)

        obj.exec_()
        return obj.numRowsAffected()

    @classmethod
    def delete(cls, table_name: str, where_str: str, params: list = []) -> int:
        query = f'DELETE FROM {table_name} WHERE {where_str}'
        obj = QSqlQuery()
        obj.prepare(query)

        for value in params:
            obj.addBindValue(value)

        obj.exec_()
        return obj.numRowsAffected()

    @classmethod
    def get(cls, table_name, where_str, params) -> dict:
        if type(params) is not list:
            params = [params]

        query = f"SELECT * FROM {table_name} WHERE {where_str}"
        obj = QSqlQuery()
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

    @classmethod
    def fetch(cls, sql, params=[]):
        if type(params) is not list:
            params = [params]

        obj = QSqlQuery()
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


class Survey(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        query = """
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                survey_datetime TEXT,
                survey_name TEXT,
                survey_comment TEXT
            )
        """
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_SURVEYS}
                """
        cls.exec(query)

    @classmethod
    def get_survey(cls, survey_id) -> dict:
        return cls.get(SQL_TABLE_SURVEYS, 'survey_id=?', [survey_id])

    @classmethod
    def insert_survey(cls, device_name: str) -> int:
        model = cls()
        model.select()
        # do not set breakstations here, you will start inserting multiple records per breakstation.
        record = model.record()
        now = datetime.now()
        record.setValue('survey_id', None)
        record.setValue('device_name', device_name)
        record.setValue('survey_datetime', now.timestamp())
        record.setValue('survey_name', now.strftime('%c'))
        record.setValue('survey_comment', '')
        # -1 is set to indicate that it will be added to the last row
        if model.insertRecord(-1, record):
            model.submitAll()
            last_insert_id = model.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert survey')

    @classmethod
    def update_survey(cls, values: dict, survey_id: int) -> int:
        return cls.update(SQL_TABLE_SURVEYS, values, 'survey_id=?', [survey_id])

    @classmethod
    def delete_survey(cls, survey_id: int) -> int:
        a = cls.delete(SQL_TABLE_STATIONS, 'survey_id=?', [survey_id])
        b = cls.delete(SQL_TABLE_SECTIONS, 'survey_id=?', [survey_id])
        c = cls.delete(SQL_TABLE_SURVEYS, 'survey_id=?', [survey_id])
        return a + b + c

    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_SURVEYS} ORDER BY survey_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_SURVEYS, table_data)

    def __init__(self):
        super().__init__()

        self.setTable(SQL_TABLE_SURVEYS)
        self.setEditStrategy(self.OnManualSubmit)
        #
        # self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYORS, 'survey_id', 'name'))
        # self.setRelation(1, QSqlRelation(SQL_TABLE_EXPLORERS, 'survey_id', 'name'))


class Section(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
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
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_SECTIONS}
                """
        cls.exec(query)

    @classmethod
    def get_section(cls, section_id) -> dict:
        return cls.get(SQL_TABLE_SECTIONS, 'section_id=?', [section_id])

    @classmethod
    def insert_section(cls, survey_id: int, section_reference_id: int, device_properties: dict) -> int:
        model = cls()
        model.select()
        # do not set breakstations here, you will start inserting multiple records per breakstation.
        record = model.record()
        now = datetime.now()
        record.setValue('section_id', None)
        record.setValue('survey_id', survey_id)
        record.setValue('section_reference_id', section_reference_id)
        record.setValue('device_properties', json.dumps(device_properties))
        record.setValue('section_name', f'Section {section_reference_id}')
        record.setValue('section_comment', '')
        # -1 is set to indicate that it will be added to the last row
        if model.insertRecord(-1, record):
            model.submitAll()
            last_insert_id = model.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert section')

    @classmethod
    def update_section(cls, values: dict, section_id: int) -> int:
        return cls.update(SQL_TABLE_SECTIONS, values, 'section_id=?', [section_id])

    @classmethod
    def delete_section(cls, section_id: int) -> int:
        a = cls.delete(SQL_TABLE_STATIONS, 'section_id=?', [section_id])
        b = cls.delete(SQL_TABLE_SECTIONS, 'section_id=?', [section_id])
        return a + b

    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_SECTIONS} ORDER BY section_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_SECTIONS, table_data)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_SECTIONS)
        self.setEditStrategy(self.OnManualSubmit)
        # self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'survey_name'))

    def flags(self, index: QModelIndex):
        flags = Qt.NoItemFlags
        if index.column() in [2, 3]:
            return flags

        return flags | Qt.ItemIsEditable | Qt.ItemIsEnabled


class Station(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        # reference_id is the "id" as provider by the Mnemo.
        # so it is a local reference id only unique to the section itself.
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_STATIONS} (
                station_id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                survey_id INTEGER,
                station_reference_id INTEGER,
                section_reference_id INTEGER,
                depth REAL,
                temperature REAL,
                azimuth_in REAL,
                azimuth_out REAL,
                length_in REAL,
                length_out REAL,
                station_name TEXT,
                station_comment TEXT
            )
        """
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_STATIONS}
                """
        cls.exec(query)

    @classmethod
    def insert_station(cls,
                       survey_id: int,
                       section_id: int,
                       section_reference_id: int,
                       station_reference_id: int,
                       length_in: float,
                       length_out: float,
                       azimuth_in: float,
                       azimuth_out: float,
                       depth: float,
                       station_properties: dict = {},
                       station_name: str = ''
                       ) -> int:
        model = cls()
        model.select()
        # do not set breakstations here, you will start inserting multiple records per breakstation.
        record = model.record()
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
        record.setValue('depth', depth)
        record.setValue('station_properties', json.dumps(station_properties))
        record.setValue('station_name', station_name)

        # -1 is set to indicate that it will be added to the last row
        if model.insertRecord(-1, record):
            model.submitAll()
            last_insert_id = model.query().lastInsertId()
            return last_insert_id

        raise SyntaxError('Database error: Could not insert station')

    @classmethod
    def update_station(cls, values: dict, station_id: int) -> int:
        return cls.update(SQL_TABLE_STATIONS, values, 'station_id=?', [station_id])


    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_STATIONS} ORDER BY station_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_STATIONS, table_data)


    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_STATIONS)
        self.setEditStrategy(self.OnManualSubmit)


class Contact(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_CONTACTS} (
                       contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT
                   )
               """
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                    DROP TABLE IF EXISTS {SQL_TABLE_CONTACTS}
                """
        cls.exec(query)

    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_CONTACTS} ORDER BY contact_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_CONTACTS, table_data)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_CONTACTS)


class Explorer(QSqlRelationalTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_EXPLORERS} (
                       b_explorer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                       DROP TABLE IF EXISTS {SQL_TABLE_EXPLORERS}
                   """
        cls.exec(query)

    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_EXPLORERS} ORDER BY explorer_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_EXPLORERS, table_data)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_EXPLORERS)
        self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))


class Surveyor(QSqlRelationalTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_SURVEYORS} (
                       b_surveyor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        cls.exec(query)

    @classmethod
    def drop_database_tables(cls):
        query = f"""
                       DROP TABLE IF EXISTS {SQL_TABLE_SURVEYORS}
                   """
        cls.exec(query)

    @classmethod
    def dump_table(cls):
        return cls.fetch(f"SELECT * FROM {SQL_TABLE_SURVEYORS} ORDER BY surveyor_id ASC")

    @classmethod
    def load_table(cls, table_data: list):
        if len(table_data) == 0:
            return 0
        return cls.insert_bulk(SQL_TABLE_SURVEYORS, table_data)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_SURVEYORS)
        self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))
