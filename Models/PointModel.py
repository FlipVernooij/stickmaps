from Models.Db import Sqlite


class Point:

    @classmethod
    def create_database_tables(cls):
        # reference_id is the "id" as provider by the Mnemo.
        # so it is a local reference id only unique to the section itself.
        query = """
            CREATE TABLE IF NOT EXISTS points (
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
        Sqlite.exec(query)

    @classmethod
    def get_point(cls, point_id):
        row = Sqlite.get('points', 'point_id=', point_id)
        survey = cls(**row)
        return survey

    def __init__(
            self,
            point_reference_id: int,
            survey_id: int,
            section_id: int,
            section_reference_id: int = None,
            point_id: int = None,
            depth: int = None,
            azimuth_in: int = None,
            azimuth_out: int = None,
            length_in: int = None,
            length_out: int = None,
            temperature: int = None,
            point_name: str = None,
            point_comment: str = None
    ):
        self.point_id = point_id
        self.point_reference_id = point_reference_id
        self.section_reference_id = section_reference_id
        self.survey_id = survey_id
        self.section_id = section_id
        self.depth = depth
        self.azimuth_in = azimuth_in
        self.azimuth_out = azimuth_out
        self.length_in = length_in
        self.length_out = length_out
        self.temperature = temperature
        self.point_name = point_name
        self.point_comment = point_comment

    def save(self):
        if self.point_name is None or self.point_name == '':
            self.point_name = f'Station {self.point_reference_id}'

        if self.point_id is None:
            self.point_id = Sqlite.insert('points', self._get_columns())
        else:
            Sqlite.update('points', self._get_columns(), 'point_id=?', {'point_id': self.survey_id})
        return self.survey_id

    def _get_columns(self):
        return {
            'point_reference_id': self.point_reference_id,
            'section_reference_id': self.section_reference_id,
            'survey_id': self.survey_id,
            'section_id': self.section_id,
            'depth': self.depth,
            'azimuth_in': self.azimuth_in,
            'azimuth_out': self.azimuth_out,
            'length_in': self.length_in,
            'length_out': self.length_out,
            'temperature': self.temperature,
            'point_name': self.point_name,
            'point_comment': self.point_comment,
        }
