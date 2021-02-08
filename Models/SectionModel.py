import json

from Models.Db import Sqlite
from Models.PointModel import Point


class Section:

    @classmethod
    def create_database_tables(cls):
        query = """
            CREATE TABLE IF NOT EXISTS sections (
                section_id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                section_reference_id INTEGER,
                device_properties TEXT,
                section_name TEXT,
                section_comment TEXT
            )
        """
        Sqlite.exec(query)

    @classmethod
    def get_section(cls, section_id):
        row = Sqlite.get('sections', 'section_id=', section_id)
        row.device_properties = json.loads(row.device_properties)
        section = cls(**row)
        section.load_points()
        return section

    def __init__(self, survey_id: int, section_id: int = None, section_reference_id: int = None, section_name: str = None, section_comment: str = None,
                 device_properties: dict = None):

        if device_properties is None:
            device_props = {}

        self.survey_id = survey_id
        self.section_id = section_id
        self.section_reference_id = section_reference_id
        self.section_name = section_name
        self.section_comment = section_comment
        self.device_properties = device_properties

        self.points = []

    def save(self):
        if self.section_name is None or self.section_name == '':
            self.section_name = f'Section {self.section_reference_id}'
        if self.section_id is None:
            self.section_id = Sqlite.insert('sections', self._get_columns())
        else:
            Sqlite.update('sections', self._get_columns(), 'section_id=?',
                          {'section_id': self.section_id})
        return self.section_id

    def load_points(self):
        rows = Sqlite.fetch('SELECT * FROM points WHERE section_id=?', [self.section_id])
        for row in rows:
            self.append_point(Point(**row))

    def append_point(self, point: Point):
        self.points.append(point)

    def _get_columns(self):
        return {
            'survey_id': self.survey_id,
            'device_properties': json.dumps(self.device_properties),
            'section_reference_id': self.section_reference_id,
            'section_name': self.section_name,
            'section_comment': self.section_comment,
        }
