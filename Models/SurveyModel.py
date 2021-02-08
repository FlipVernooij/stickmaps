import time
from datetime import datetime

from Models.SectionModel import Section
from Models.Db import Sqlite


class Survey(Sqlite):

    @classmethod
    def create_database_tables(cls):
        query = """
            CREATE TABLE IF NOT EXISTS surveys (
                survey_id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT,
                survey_datetime INTEGER,
                survey_name TEXT,
                survey_comment TEXT
            )
        """
        Sqlite.exec(query)
        query = """
                   CREATE TABLE IF NOT EXISTS contacts (
                       contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       name TEXT
                   )
               """
        Sqlite.exec(query)

        query = """
                   CREATE TABLE IF NOT EXISTS b_explorers (
                       b_explorer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        Sqlite.exec(query)

        query = """
                   CREATE TABLE IF NOT EXISTS b_surveyors (
                       b_surveyor_id INTEGER PRIMARY KEY AUTOINCREMENT,
                       survey_id INTEGER, 
                       contact_id INTEGER,
                       name TEXT
                   )
               """
        Sqlite.exec(query)

    @classmethod
    def get_survey(cls, survey_id):
        row = Sqlite.get('surveys', 'survey_id=', survey_id)
        survey = cls(**row)
        survey.load_sections()
        return survey

    def __init__(self,
                 device_name,
                 survey_name=None,
                 survey_comment=None,
                 survey_datetime=None,
                 survey_id=None,
                 ):
        self.survey_id = survey_id
        self.survey_name = survey_name
        self.survey_comment = survey_comment
        if survey_datetime is None:
            self.survey_datetime = int(time.time())
        else:
            self.survey_datetime = survey_datetime
        self.device_name = device_name

        self.sections = []

    def save(self):
        if self.survey_id is None:
            self.survey_id = Sqlite.insert('surveys', self._get_columns())
        else:
            Sqlite.update('surveys', self._get_columns(), 'survey_id=?', {'survey_id': self.survey_id})
        return self.survey_id

    def load_sections(self):
        rows = Sqlite.fetch('SELECT * FROM sections WHERE survey_id=?', [self.survey_id])
        for row in rows:
            section = Section(**row)
            section.load_points()
            self.append_section(section)

    def append_section(self, section: Section):
        self.sections.append(section)

    def _get_columns(self):
        return {
            'device_name': self.device_name,
            'survey_name': self.survey_name,
            'survey_comment': self.survey_comment,
            'survey_datetime': self.survey_datetime
        }
