from datetime import datetime

from DataStructs.Section import SectionStruct


class SurveyStruct:

    def __init__(self):
        self.explorers = []
        self.date = datetime.now()
        self.sections = []

    def add_explorer(self, name):
        self.add_explorers([name])

    def add_explorers(self, names):
        self.explorers.extend(names)

    def add_section(self, data: SectionStruct):
        self.sections.append(data)
