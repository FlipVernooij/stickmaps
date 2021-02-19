import json
import sys
from datetime import datetime

from PySide6.QtSql import QSqlTableModel, QSqlQuery, QSqlRelationalTableModel, QSqlRelation, QSqlDatabase

from Config.Constants import SQL_TABLE_POINTS, SQL_TABLE_SECTIONS, SQL_TABLE_SURVEYS, SQL_TABLE_CONTACTS, \
    SQL_TABLE_EXPLORERS, SQL_TABLE_SURVEYORS, SQL_DB_LOCATION
from Gui.Dialogs import ErrorDialog


class QueryMixin:

    @classmethod
    def init_db(cls):
        db = QSqlDatabase.addDatabase('QSQLITE')
        db.setDatabaseName(SQL_DB_LOCATION)
        if not db.open():
            ErrorDialog.show("Database Error: {}".format(db.lastError()))

    @classmethod
    def create_tables(cls):
        Survey.create_database_tables()
        Section.create_database_tables()
        Point.create_database_tables()
        Contacts.create_database_tables()
        Surveyors.create_database_tables()
        Explorers.create_database_tables()

    @classmethod
    def exec(cls, sql):
        query = QSqlQuery()
        return query.exec_(sql)

    @classmethod
    def insert(cls, table_name: str, values: dict):
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
    def update(cls, table_name: str, values: dict, where_str: str, params: list = []):
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
    def get(cls, table_name, where_str, params):
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
    def insert_survey(cls, device_name: str) -> int:
        model = cls()
        model.select()
        # do not set breakpoints here, you will start inserting multiple records per breakpoint.
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

        ErrorDialog.show("Database Error: {}".format(model.query().lastError()))
        sys.exit(1)

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
    def insert_section(cls, survey_id: int, section_reference_id: int, device_properties: dict) -> int:
        model = cls()
        model.select()
        # do not set breakpoints here, you will start inserting multiple records per breakpoint.
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

        ErrorDialog.show("Database Error: {}".format(model.query().lastError()))
        sys.exit(1)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_SECTIONS)
        self.setEditStrategy(self.OnManualSubmit)
        # self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'survey_name'))


class Point(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        # reference_id is the "id" as provider by the Mnemo.
        # so it is a local reference id only unique to the section itself.
        query = f"""
            CREATE TABLE IF NOT EXISTS {SQL_TABLE_POINTS} (
                point_id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                survey_id INTEGER,
                point_reference_id INTEGER,
                section_reference_id INTEGER,
                depth REAL,
                temperature REAL,
                azimuth_in REAL,
                azimuth_out REAL,
                length_in REAL,
                length_out REAL,
                point_name TEXT,
                point_comment TEXT
            )
        """
        cls.exec(query)

    @classmethod
    def insert_point(cls,
                      survey_id: int,
                      section_id: int,
                      section_reference_id: int,
                      point_reference_id: int,
                      length_in: float,
                      length_out: float,
                      azimuth_in: float,
                      azimuth_out: float,
                      depth: float,
                      point_properties: dict = {}
                      ) -> int:
        model = cls()
        model.select()
        # do not set breakpoints here, you will start inserting multiple records per breakpoint.
        record = model.record()
        now = datetime.now()
        record.setValue('point_id', None)
        record.setValue('section_id', section_id)
        record.setValue('survey_id', survey_id)
        record.setValue('section_reference_id', section_reference_id)
        record.setValue('point_reference_id', point_reference_id)
        record.setValue('length_in', length_in)
        record.setValue('length_out', length_out)
        record.setValue('azimuth_in', azimuth_in)
        record.setValue('azimuth_out', azimuth_out)
        record.setValue('depth', depth)
        record.setValue('point_properties', json.dumps(point_properties))

        # -1 is set to indicate that it will be added to the last row
        if model.insertRecord(-1, record):
            model.submitAll()
            last_insert_id = model.query().lastInsertId()
            return last_insert_id

        ErrorDialog.show("Database Error: {}".format(model.query().lastError()))
        sys.exit(1)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_POINTS)
        self.setEditStrategy(self.OnManualSubmit)

        # self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'survey_name'))
        # self.setRelation(2, QSqlRelation(SQL_TABLE_SECTIONS, 'section_id', 'section_name'))


class Contacts(QSqlTableModel, QueryMixin):

    @classmethod
    def create_database_tables(cls):
        query = f"""
                   CREATE TABLE IF NOT EXISTS {SQL_TABLE_CONTACTS} (
                       contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT
                   )
               """
        cls.exec(query)

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_CONTACTS)


class Explorers(QSqlRelationalTableModel, QueryMixin):

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

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_EXPLORERS)
        self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))


class Surveyors(QSqlRelationalTableModel, QueryMixin):

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

    def __init__(self):
        super().__init__()
        self.setTable(SQL_TABLE_SURVEYORS)
        self.setRelation(1, QSqlRelation(SQL_TABLE_SURVEYS, 'survey_id', 'name'))
        self.setRelation(2, QSqlRelation(SQL_TABLE_CONTACTS, 'contact_id', 'name'))
