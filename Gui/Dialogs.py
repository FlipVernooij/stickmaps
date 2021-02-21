from PySide6.QtCore import QDateTime
from PySide6.QtGui import Qt
from PySide6.QtSql import QSqlTableModel
from PySide6.QtWidgets import QErrorMessage, QDialog, QTableView, QHBoxLayout, QMessageBox, QApplication, QFormLayout, \
    QLineEdit, QDateTimeEdit, QTextEdit, QDialogButtonBox, QVBoxLayout

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME
from Models.TableModels import Section, Survey, Point


class ErrorDialog:

    errorMessages = {
        'UNKNOWN_ERROR': {
            'title': "Unknown error occurred",
            'body': "Bang head against screen and try again."
        },
        'NO_DEVICE_FOUND': {
            'title': "Could not find connected device",
            'body': """
                <h3>Could not connect to your Mnemo</h3>
                <p>Make sure it is properly connected.</p>
                <p>Select &gt;Ok&lt; after connection the Mnemo to enable communication</p>
                
            """,
            'status': "Connection error"
        },
        'NO_DATA_FOUND': {
            'title': "No data found",
            'body': """
                            <h3>Could not read any data on your Mnemo.</h3>
                            <p>Please make sure you select &gt;OK&lt; on the first menu-screen on the Mnemo in order to enable communications. </p>
                            <p>If this message re-appears, you most probably have NO DATA on your device.</p>
                        """,
            'status': "Failed reading Mnemo."
        }
    }

    @classmethod
    def show_error_key(cls, parent_window, error_key):

        try:
            title = cls.errorMessages[error_key]['title']
            body = cls.errorMessages[error_key]['body']
        except:
            title = cls.errorMessages['UNKNOWN_ERROR']['title']
            body = cls.errorMessages['UNKNOWN_ERROR']['body'] + "<p><b>" + error_key + "</b></p>"
            print(error_key)

        window = QErrorMessage(parent_window)
        window.resize(500, 250)
        window.setWindowTitle(title)
        window.showMessage(body)
        try:
            if cls.errorMessages[error_key]['status']:
                parent_window.statusBar().showMessage(cls.errorMessages[error_key]['status'], MAIN_WINDOW_STATUSBAR_TIMEOUT)
        except:
            pass

        window.show()

    @classmethod
    def show(cls, message):
        # how do I know or i am in a main window... or headless
        if QApplication.instance() is not None:
            QMessageBox.warning(None, APPLICATION_NAME, message)
        else:
            print(f"ERROR: {message}")


class EditSurveysDialog(QDialog):

    _instance_ = None

    @classmethod
    def display(cls, parent):
        cls._instance_ = EditSurveysDialog(parent)
        cls._instance_.show()

    def __init__(self, parent):
        super(EditSurveysDialog, self).__init__(parent)
        model = Survey()
        model.setEditStrategy(QSqlTableModel.OnFieldChange)

        model.setHeaderData(0, Qt.Horizontal, "Survey ID")
        model.setHeaderData(1, Qt.Horizontal, "Device name")
        model.setHeaderData(2, Qt.Horizontal, "Survey date/time")
        model.setHeaderData(3, Qt.Horizontal, "Survey name")
        model.setHeaderData(4, Qt.Horizontal, "Survey comment")
        model.select()

        view = QTableView(self)
        view.setModel(model)
        view.resizeColumnsToContents()


        self.setWindowTitle('Edit surveys')
        self.resize(800, 400)

        layout = QHBoxLayout()
        layout.addWidget(view)
        self.setLayout(layout)


class EditSurveyDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.survey = Survey.get_survey(item.section_id)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.name_field = QLineEdit(self.survey['survey_name'])
        self.name_field.setClearButtonEnabled(True)
        layout.addRow('&Name', self.name_field)

        # should use QTime as argument here? survey['survey_datetime']
        time = QDateTime()
        time.setSecsSinceEpoch(round(float(self.survey['survey_datetime'])))
        self.datetime_field = QDateTimeEdit(time)
        layout.addRow('&Date', self.datetime_field)

        self.device_field = QLineEdit(self.survey['device_name'])
        self.device_field.setClearButtonEnabled(True)
        layout.addRow('&Device', self.device_field)

        self.comment_field = QTextEdit(self.survey['survey_comment'])
        layout.addRow('&Comment', self.comment_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        layout.addRow(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        self.setWindowTitle('Edit Survey')
        self.resize(800, 400)
        self.setLayout(layout)

    def save(self):
        survey_dict = self.survey
        survey_dict['survey_name'] = self.name_field.text()
        survey_dict['survey_comment'] = self.comment_field.toPlainText()
        survey_dict['device_name'] = self.device_field.text()
        time = self.datetime_field.dateTime().toPython()
        survey_dict['survey_datetime'] = time.timestamp()

        tree = self.parentWidget()
        model = tree.model()
        model.update_survey(data=survey_dict, index=tree.selectedIndexes()[0])
        self.close()

    def reset(self):
        survey_dict = self.survey
        self.name_field.setText(survey_dict['survey_name'])
        self.comment_field.setText(survey_dict['survey_comment'])
        self.device_field.setText(survey_dict['device_name'])
        time = QDateTime()
        time.setSecsSinceEpoch(round(float(survey_dict['survey_datetime'])))
        self.datetime_field.setTime(time)

    def cancel(self):
        self.close()


class EditSectionsDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent.main_window)
        self.tree_view = parent
        self.survey_id = item.section_id
        self.item = item
        self.setWindowTitle('Edit sections')
        self.resize(800, 400)
        model = Section()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'survey_id={self.survey_id}')

        model.setHeaderData(0, Qt.Horizontal, "Survey id")
        model.setHeaderData(1, Qt.Horizontal, "Section id")
        model.setHeaderData(2, Qt.Horizontal, "Device reference id")
        model.setHeaderData(3, Qt.Horizontal, "Device properties")
        model.setHeaderData(4, Qt.Horizontal, "Section name")
        model.setHeaderData(5, Qt.Horizontal, "Section comment")

        view = QTableView(self)
        view.setSelectionMode(QTableView.NoSelection)
        view.setAlternatingRowColors(True)
        view.setShowGrid(True)
        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        view.setModel(model)
        view.setColumnHidden(0, True)  # survey_id
        view.setColumnHidden(1, True)  # section_id

        view.horizontalHeader().setStretchLastSection(True)

        view.resizeColumnsToContents()
        model.select()
        self.table_view = view
        self.setLayout(layout)

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.tree_view.model().reload_sections(self.item)
        self.close()

    def reset(self):
        table = self.table_view
        model = table.model()

        model.revertAll()

    def cancel(self):
        self.close()


class EditSectionDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.section = Section.get_section(item.section_id)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.id_field = QLineEdit(str(self.section['section_reference_id']))
        self.id_field.setClearButtonEnabled(False)
        self.id_field.setDisabled(True)
        layout.addRow('&Device id', self.id_field)

        self.name_field = QLineEdit(self.section['section_name'])
        self.name_field.setClearButtonEnabled(True)
        layout.addRow('&Name', self.name_field)

        self.comment_field = QTextEdit(self.section['section_comment'])
        layout.addRow('&Comment', self.comment_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        layout.addRow(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        self.setWindowTitle('Edit Section')
        self.resize(800, 400)
        self.setLayout(layout)

    def save(self):
        section_dict = self.section
        section_dict['section_name'] = self.name_field.text()
        section_dict['section_comment'] = self.comment_field.toPlainText()

        tree = self.parentWidget()
        model = tree.model()
        model.update_section(data=section_dict, index=tree.selectedIndexes()[0])
        self.close()

    def reset(self):
        section_dict = self.section
        self.name_field.setText(section_dict['section_name'])
        self.comment_field.setText(section_dict['section_comment'])

    def cancel(self):
        self.close()


class EditPointsDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent.main_window)
        self.tree_view = parent
        self.section_id = item.section_id
        self.item = item
        self.setWindowTitle('Edit points')
        self.resize(800, 400)
        model = Point()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'section_id={self.section_id}')

        model.setHeaderData(0, Qt.Horizontal, "Survey id")
        model.setHeaderData(1, Qt.Horizontal, "Section id")
        model.setHeaderData(2, Qt.Horizontal, "Point id")
        model.setHeaderData(3, Qt.Horizontal, "Device reference id")
        model.setHeaderData(4, Qt.Horizontal, "Device section reference id")
        model.setHeaderData(5, Qt.Horizontal, "Depth")
        model.setHeaderData(6, Qt.Horizontal, "Temperature")
        model.setHeaderData(7, Qt.Horizontal, "Azimuth in")
        model.setHeaderData(8, Qt.Horizontal, "Azimuth out")
        model.setHeaderData(9, Qt.Horizontal, "Length in")
        model.setHeaderData(10, Qt.Horizontal, "Length out")
        model.setHeaderData(11, Qt.Horizontal, "Point name")
        model.setHeaderData(12, Qt.Horizontal, "Point Comment")

        view = QTableView(self)
        view.setSelectionMode(QTableView.NoSelection)
        view.setAlternatingRowColors(True)
        view.setShowGrid(True)
        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        view.setModel(model)
        view.setColumnHidden(0, True)  # survey_id
        view.setColumnHidden(1, True)  # section_id
        view.setColumnHidden(2, True)  # section_id
        view.setColumnHidden(4, True)  # section_id

        view.horizontalHeader().setStretchLastSection(True)

        view.resizeColumnsToContents()
        model.select()
        self.table_view = view
        self.setLayout(layout)

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.tree_view.model().reload_points(self.item)
        self.close()

    def reset(self):
        table = self.table_view
        model = table.model()

        model.revertAll()

    def cancel(self):
        self.close()


