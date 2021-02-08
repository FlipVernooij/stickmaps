from PySide6.QtGui import QStandardItemModel, QStandardItem, QIcon

from Config.Constants import TREE_ICON_SURVEY, TREE_ICON_SECTION, TREE_ICON_POINT
from Models.SurveyModel import Survey


class SurveyCollection(QStandardItemModel):

    _instance_ = None

    @classmethod
    def get_instance(cls):
        if cls._instance_ is None:
            cls._instance_ = cls()
        return cls._instance_

    def __init__(self, *args, **kwargs):
        super(self, QStandardItemModel, *args, **kwargs)
        self.parent_item = self.invisibleRootItem()

    def add_survey(self, survey: Survey):
        survey_item = QStandardItem(QIcon(TREE_ICON_SURVEY), survey.survey_name)
        survey_item.setData(survey)
        survey_item.load_sections()
        for section in survey.sections:
            section_item = QStandardItem(QIcon(TREE_ICON_SECTION), section.section_name)
            section_item.setData(section)
            survey_item.child(section_item)
            for point in section.points:
                point_item = QStandardItem(QIcon(TREE_ICON_POINT), point.point_name)
                point_item.setData(point)
                section_item.child(point_item)




    def get_view_model(self):
        return self.view_model
