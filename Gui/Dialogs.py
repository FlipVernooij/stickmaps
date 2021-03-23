import PySide6
from PySide6 import QtCore
from PySide6.QtCore import QDateTime, QSysInfo, QSettings
from PySide6.QtGui import Qt, QFont
from PySide6.QtSql import QSqlTableModel
from PySide6.QtWidgets import QErrorMessage, QDialog, QTableView, QHBoxLayout, QMessageBox, QApplication, QFormLayout, \
    QLineEdit, QDateTimeEdit, QTextEdit, QDialogButtonBox, QVBoxLayout, QDoubleSpinBox, QListWidget, \
    QCheckBox, QComboBox, QSpinBox, QLabel, QPushButton

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME, MNEMO_DEVICE_DESCRIPTION, DEBUG, \
    MNEMO_DEVICE_NAME, MNEMO_BAUDRATE, MNEMO_TIMEOUT, MNEMO_CYCLE_COUNT, SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT, \
    SQL_DB_LOCATION
from Gui.Delegates.FormElements import DropDown
from Models.TableModels import Section, Survey, Station
from Utils.Settings import Preferences

import traceback


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
        },
        'SERIAL_ERROR': {
            'title': "Could not connect to Mnemo",
            'body': """
                        <h3>There was an error setting up the serial connection</h3>
                        <p>This is most likely due to the default permissions set to serial usb devices by udev</p>
                        <dl>
                            <dt>Quick fix:</dt>
                            <dd><code> sudo chmod 0777 /dev/ttyACM*</code> </dd>
                            <dt>Permanent fix:</dt>
                            <dd>
                                &nbsp;&nbsp;&nbsp;&nbsp;<code>sudoedit /etc/udev/rules.d/50-myusb.rules </code>
                                <br />Change: <br/>
                                &nbsp;&nbsp;&nbsp;&nbsp;<code> KERNEL=="ttyACM[0-9]*",MODE="0666"</code> 
                                
                            </dd>
                        </dl>
                    """
        },
        'NO_DATA_TO_BE_WRITTEN': {
            'title': "No data to write",
            'body': """
                <h3>Mnemo has no data</h3>
                <p>
                    We connected successfully to the Mnemo, yet we didn't found any data.<br />
                    If you are sure that there should be data on your device, follow the following steps:
                </p>
                <ol>
                    <li>Wait for 20 seconds</li>
                    <li>Turn OFF your Mnemo</li>
                    <li>Turn ON your Mnemo</li>
                    <li>Restart the sync in Stickmaps</li>
                </ol>
            """
        }
    }

    @classmethod
    def show_error_key(cls, parent_window, error_key: str, error_exception: Exception = None):

        try:
            title = cls.errorMessages[error_key]['title']
            body = cls.errorMessages[error_key]['body']
        except:
            title = cls.errorMessages['UNKNOWN_ERROR']['title']
            body = cls.errorMessages['UNKNOWN_ERROR']['body'] + "<p><b>" + error_key + "</b></p>"

        if error_exception is not None:
            body = f'{body}<p><br /><code>{str(error_exception)}</code><br /></p>'
            if Preferences.get('debug', DEBUG, bool) is True:
                body = f'{body}<p><code>{traceback.format_exc(10)}</code>'

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


class PreferencesDialog(QDialog):
    FORMS = {
        "General": {
            "fields": [
                {
                    "label": "CPU architecture",
                    "form_field": "label",
                    "value": f'{QSysInfo.currentCpuArchitecture()}/{QSysInfo.buildCpuArchitecture()}'
                },
                {
                    "label": "Compiled architecture",
                    "form_field": "label",
                    "value": f'{QSysInfo.buildAbi()}'
                },
                {
                    "label": "Operating system",
                    "form_field": "label",
                    "value": f'{QSysInfo.prettyProductName()}'
                },
                {
                    "label": "Kernel version",
                    "form_field": "label",
                    "value": f'{QSysInfo.kernelType()} - {QSysInfo.kernelVersion()}'
                },
                {
                    "label": "QT version",
                    "form_field": "label",
                    "value": f'{QtCore.__version__}'
                },
                {
                    "label": "PySide version",
                    "form_field": "label",
                    "value": f'{PySide6.__version__}'
                },
                {
                    "label": "Enable developer-mode",
                    "info": "Enables some advanced configuration-options and debugging tools, USE WITH CARE!",
                    "form_field": "check_box",
                    "settings_key": "debug",
                    "default_value": DEBUG

                }
            ]
        },
        "Mnemo": {
            "fields": [
                {
                    "label": "Device name",
                    "info": "This is the label used as the \"device name\" within your survey.",
                    "form_field": "text_line",
                    "settings_key": "mnemo_device_name",
                    "default_value": MNEMO_DEVICE_NAME
                },
                {
                  "label": "Read cycles",
                  "info": "The amount of tries we will try to fetch more data from the Mnemo serial connection.",
                    "form_field": "spinner",
                    "min": 10,
                    "max": 100,
                    "settings_key": "mnemo_cycle_count",
                    "default_value": MNEMO_CYCLE_COUNT,
                },
                {
                    "label": "Device ",
                    "info": "The device description to look for when scanning your usb devices for a Mnemo connection.",
                    "form_field": "text_line",
                    "settings_key": "mnemo_device_description",
                    "default_value": MNEMO_DEVICE_DESCRIPTION,
                    "dev_only": True
                },
                {
                    "label": "Baudrate",
                    "info": "The speed used to read out your Mnemo.",
                    "form_field": "combo_box",
                    "options": [
                        "9600",
                        "19200",
                        "38400",
                        "57600"
                    ],
                    "settings_key": "mnemo_baudrate",
                    "default_value": MNEMO_BAUDRATE
                },
                {

                    "label": "Timeout",
                    "info": "Connection timeout",
                    "form_field": "spinner",
                    "min": 0,
                    "max": 10,
                    "settings_key": "mnemo_timeout",
                    "default_value": MNEMO_TIMEOUT,
                    "dev_only": True
                },
            ]
        },
        "Debug": {
            "dev_only": True,
            "fields": [
                {
                    "label": "Sqlite database location",
                    "info": "Use \":memory:\" to create a fast yet volatile database in RAM.",
                    "form_field": "text_line",
                    "settings_key": "sql_db_location",
                    "default_value": SQL_DB_LOCATION,
                },
                {
                    "label": "QSettings raw data",
                    "form_field": "label_ml",
                    "value_from_function": "_settings_as_string"
                },
                {
                    "label": "Reset settings",
                    "form_field": "button",
                    "button_label": "reset",
                    "action": "_reset_settings"
                }
            ]

        }
    }

    def _settings_as_string(self, element: dict) -> str:
        data = Preferences.get_everything()
        r = []
        for key in data:
            r.append(f'\t{key} = {data[key]}')

        return '\n'.join(r)

    def _reset_settings(self, event):
        response = QMessageBox.question(self, 'Reset ALL settings?', 'You can not undo this, continue?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.No:
            return

        s = QSettings()
        all_keys = s.allKeys()
        for key in all_keys:
            s.remove(key)

        self.generate_form(self.current_form)


    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.setWindowTitle('Preferences')
        self.resize(800, 400)

        self.form_changed = False
        self.current_form = "General"

        self.list_widget = QListWidget()
        self.generate_chapters()


        self.list_widget.setMaximumWidth(150)

        layout = QHBoxLayout()

        layout.addWidget(self.list_widget)

        self.form_layout = QFormLayout()
        self.form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.form_layout.setLabelAlignment(Qt.AlignRight)
        self.form_layout.setContentsMargins(10, 0, 20, 0)
        self.generate_form(self.current_form)
        layout.addLayout(self.form_layout)

        o_layout = QVBoxLayout()
        o_layout.addLayout(layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.close)
        o_layout.addWidget(buttons)

        self.setLayout(o_layout)

    def save(self):
        for field in self.FORMS[self.current_form]['fields']:
            if 'settings_key' in field and 'form_element' in field:
                Preferences.set(field['settings_key'], self.get_field_value(field))

        self.generate_chapters()
        self.main_window.toggle_debug_console(Preferences.get('debug', DEBUG, bool))

        self.form_changed = False

    def close(self, event=None):
        if self.form_changed is True:
            response = QMessageBox.question(self, 'Ignore unsaved changes?', 'You have unsaved changes, continue?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.No:
                return

        super().close()

    def chapter_clicked(self, event):
        if self.form_changed is True:
            response = QMessageBox.question(self, 'Ignore unsaved changes?', 'You have unsaved changes, continue?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.No:
                return

        self.form_changed = False
        self.current_form = event.text()


        self.generate_form(self.current_form)

    def field_changed(self, arg=None):
        self.form_changed = True

    def generate_chapters(self):
        while self.list_widget.count() > 0:
            self.list_widget.takeItem(self.list_widget.count()-1)

        for item in self.FORMS.keys():
            if 'dev_only' in self.FORMS[item] and self.FORMS[item]['dev_only'] is True:
                if Preferences.get('debug', DEBUG, bool) is False:
                    continue

            self.list_widget.addItem(item)

        self.list_widget.itemClicked.connect(self.chapter_clicked)

    def generate_form(self, key):
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(self.form_layout.rowCount() - 1)

        for i, element in enumerate(self.FORMS[key]['fields']):
            if 'default_value' in element:
                element['default_value'] = Preferences.get(element['settings_key'], element['default_value'])
            self.FORMS[key]['fields'][i]['form_element'] = self.get_field(element)
            label = QLabel(element['label'])
            label.setMinimumWidth(150)
            if 'info' in element:
                label.setToolTip(f"{element['info']}")

            self.form_layout.addRow(label, self.FORMS[key]['fields'][i]['form_element'])

    def get_field(self, element: dict):
        f = element['form_field']
        if f == 'text_line':
            el = QLineEdit(self)
            el.setText(str(element['default_value']))
            el.setClearButtonEnabled(True)
            el.textChanged.connect(self.field_changed)
        elif f == 'check_box':
            el = QCheckBox(self)
            el.setChecked(bool(int(element['default_value'])))
            el.stateChanged.connect(self.field_changed)
        elif f == 'combo_box':
            el = QComboBox(self)
            el.addItems(element['options'])
            el.setCurrentText(str(element['default_value']))
            el.currentTextChanged.connect(self.field_changed)
        elif f == 'spinner':
            el = QSpinBox(self)
            el.setValue(int(element['default_value']))
            el.setMinimum(element['min'])
            el.setMaximum(element['max'])
            el.valueChanged.connect(self.field_changed)
        elif f == 'button':
            el = QPushButton(element['button_label'])
            el.clicked.connect(getattr(self, element['action']))
        elif f == 'label':
            if "value_from_function" in element:
                element['value'] = getattr(self, element["value_from_function"])(element)
            el = QLabel(element['value'])
        elif f == 'label_ml':
            if "value_from_function" in element:
                element['value'] = getattr(self, element["value_from_function"])(element)
            el = QLabel(element['value'])
            el.setWordWrap(True)
        else:
            raise AttributeError(f'Unknown form_field in preferences plain: "{f}"')

        if 'dev_only' in element and element['dev_only'] is True:
            if Preferences.get('debug', DEBUG, bool) is False:
                el.setDisabled(True)

        el.setMinimumWidth(200)

        return el

    def get_field_value(self, element: dict):
        f = element['form_field']
        e = element['form_element']
        if f == 'text_line':
            return e.text()
        elif f == 'check_box':
            return int(e.isChecked())
        elif f == 'combo_box':
            return e.currentText()
        elif f == 'spinner':
            return e.value()
        else:
            raise AttributeError(f'Unknown form_field in preferences plain: "{f}"')


class EditSurveysDialog(QDialog):

    _instance_ = None

    @classmethod
    def display(cls, parent):
        cls._instance_ = EditSurveysDialog(parent)
        cls._instance_.show()

    def __init__(self, parent):
        super(EditSurveysDialog, self).__init__(parent)
        model = parent.sql_manager.factor(Survey)
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)

        model.setHeaderData(0, Qt.Horizontal, "Survey ID")
        model.setHeaderData(1, Qt.Horizontal, "Device name")
        model.setHeaderData(2, Qt.Horizontal, "Device properties")
        model.setHeaderData(3, Qt.Horizontal, "Date & time")
        model.setHeaderData(4, Qt.Horizontal, "Survey name")
        model.setHeaderData(5, Qt.Horizontal, "Survey comment")
        model.select()

        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setSelectionMode(QTableView.NoSelection)
        view.setColumnWidth(0, 75)
        view.setColumnWidth(1, 100)
        view.setColumnWidth(2, 110)
        view.setColumnWidth(3, 160)
        view.setColumnWidth(4, 140)
        view.horizontalHeader().setStretchLastSection(True)


        if Preferences.debug() is False:
            view.setColumnHidden(0, True)
            view.setColumnHidden(2, True)

        self.setWindowTitle('Edit surveys')
        self.resize(800, 400)

        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)


        self.setLayout(layout)
        self.table_view = view
        self.tree_view = parent.tree_view

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.tree_view.model().reload_model()
        self.close()

    def reset(self):
        table = self.table_view
        model = table.model()

        model.revertAll()

    def cancel(self):
        self.close()


class EditSurveyDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.survey = parent.main_window.sql_manager.factor(Survey).get_survey(item.survey_id)

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

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
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
        self.survey_id = item.survey_id
        self.item = item
        self.setWindowTitle('Edit sections')
        self.resize(800, 400)

        model = parent.main_window.sql_manager.factor(Section)
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'survey_id={self.survey_id}')

        model.setHeaderData(0, Qt.Horizontal, "Survey id")
        model.setHeaderData(1, Qt.Horizontal, "Section id")
        model.setHeaderData(2, Qt.Horizontal, "Device reference id")
        model.setHeaderData(3, Qt.Horizontal, "Survey direction")
        model.setHeaderData(4, Qt.Horizontal, "Device properties")
        model.setHeaderData(5, Qt.Horizontal, "Section name")
        model.setHeaderData(6, Qt.Horizontal, "Section comment")
        model.select()

        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setSelectionMode(QTableView.NoSelection)
        view.setColumnWidth(0, 60)
        view.setColumnWidth(1, 70)
        view.setColumnWidth(2, 110)
        view.setColumnWidth(3, 100)
        view.setColumnWidth(4, 120)
        view.setColumnWidth(5, 140)
        view.horizontalHeader().setStretchLastSection(True)

        delegate = DropDown(self)
        delegate.setOptions((SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT))
        view.setItemDelegateForColumn(3, delegate)

        view.setColumnHidden(1, True)  # survey_id
        if Preferences.debug() is False:
            view.setColumnHidden(0, True)  # section_id
            view.setColumnHidden(4, True)  # section_id

        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)




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
        self.section = parent.main_window.sql_manager.factor(Section).get_section(item.section_id)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.id_field = QLineEdit(str(self.section['section_reference_id']))
        self.id_field.setClearButtonEnabled(False)
        self.id_field.setDisabled(True)
        layout.addRow('&Section id', self.id_field)

        self.name_field = QLineEdit(self.section['section_name'])
        self.name_field.setClearButtonEnabled(True)
        layout.addRow('&Name', self.name_field)

        self.direction_field = QComboBox(self)
        self.direction_field.addItem(SURVEY_DIRECTION_IN)
        self.direction_field.addItem(SURVEY_DIRECTION_OUT)
        self.direction_field.setCurrentText(self.section['direction'])
        layout.addRow('&Direction', self.direction_field)

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
        section_dict['direction'] = self.direction_field.currentText()

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


class EditStationsDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent.main_window)
        self.tree_view = parent
        self.section_id = item.section_id
        self.item = item
        self.setWindowTitle('Edit stations WTF')
        self.resize(800, 400)
        model = parent.main_window.sql_manager.factor(Station)
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'section_id={self.section_id}')


        model.setHeaderData(0, Qt.Horizontal, "Station id")
        model.setHeaderData(1, Qt.Horizontal, "Section id")
        model.setHeaderData(2, Qt.Horizontal, "Survey id")
        model.setHeaderData(3, Qt.Horizontal, "Device reference id")
        model.setHeaderData(4, Qt.Horizontal, "Device section reference id")
        model.setHeaderData(5, Qt.Horizontal, "Station name")
        model.setHeaderData(6, Qt.Horizontal, "Length in")
        model.setHeaderData(7, Qt.Horizontal, "Azimuth in")
        model.setHeaderData(8, Qt.Horizontal, "Depth")
        model.setHeaderData(9, Qt.Horizontal, "Azimuth out")
        model.setHeaderData(10, Qt.Horizontal, "Azimuth")
        model.setHeaderData(11, Qt.Horizontal, "Length out")
        model.setHeaderData(12, Qt.Horizontal, "Station Comment")
        model.setHeaderData(13, Qt.Horizontal, "Device properties")

        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.setSelectionMode(QTableView.NoSelection)
        view.setColumnWidth(0, 60)
        view.setColumnWidth(1, 70)
        view.setColumnWidth(2, 110)
        view.setColumnWidth(3, 100)
        view.setColumnWidth(4, 120)
        view.setColumnWidth(5, 140)
        view.setColumnWidth(6, 140)
        view.setColumnWidth(7, 140)
        view.setColumnWidth(8, 140)
        view.setColumnWidth(9, 140)
        view.setColumnWidth(10, 140)
        view.setColumnWidth(11, 140)
        view.setColumnWidth(12, 140)
        view.horizontalHeader().setStretchLastSection(True)

        view.setColumnHidden(1, True)  # survey_id
        view.setColumnHidden(2, True)  # survey_id
        if Preferences.debug() is False:
            view.setColumnHidden(0, True)  # section_id
            view.setColumnHidden(4, True)  # section_id
            view.setColumnHidden(13, True)  # section_id

        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        view.horizontalHeader().setStretchLastSection(True)

        view.resizeColumnsToContents()
        model.select()
        self.table_view = view
        self.setLayout(layout)

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.tree_view.model().reload_stations(self.item)
        self.close()

    def reset(self):
        table = self.table_view
        model = table.model()

        model.revertAll()

    def cancel(self):
        self.close()


class EditStationDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.station = parent.main_window.sql_manager.factor(Station).get_station(item.station_id)

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.id_field = QLineEdit(str(self.station['station_reference_id']))
        self.id_field.setClearButtonEnabled(False)
        self.id_field.setDisabled(True)
        layout.addRow('&Station id', self.id_field)

        self.name_field = QLineEdit(self.station['station_name'])
        self.name_field.setClearButtonEnabled(True)
        layout.addRow('&Name', self.name_field)

        self.comment_field = QTextEdit(self.station['station_comment'])
        layout.addRow('&Comment', self.comment_field)

        self.length_in = QDoubleSpinBox()
        self.length_in.setMaximum(1000)
        self.length_in.setMinimum(0)
        self.length_in.setValue(self.station['length_in'])
        layout.addRow('&Length in', self.length_in)

        self.azimuth_in = QDoubleSpinBox()
        self.azimuth_in.setMaximum(360)
        self.azimuth_in.setMinimum(0)
        self.azimuth_in.setValue(self.station['azimuth_in'])
        layout.addRow('&Azimuth in', self.azimuth_in)

        self.depth = QDoubleSpinBox()
        self.depth.setMaximum(0)
        self.depth.setMinimum(200)
        self.depth.setValue(self.station['depth'])
        layout.addRow('&Depth', self.depth)

        self.temperature = QDoubleSpinBox()
        if isinstance(self.station['temperature'], float):
            self.temperature.setValue(self.station['temperature'])
        else:
            self.temperature.setValue(0.0)

        layout.addRow('&Temperature', self.temperature)

        self.azimuth_out = QDoubleSpinBox()
        self.azimuth_out.setMaximum(360)
        self.azimuth_out.setMinimum(0)
        self.azimuth_out.setValue(self.station['azimuth_out'])
        layout.addRow('&Azimuth out', self.azimuth_out)

        self.length_out = QDoubleSpinBox()
        self.length_out.setMaximum(1000)
        self.length_out.setMinimum(0)
        self.length_out.setValue(self.station['length_out'])
        layout.addRow('&Length out', self.length_out)


        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        layout.addRow(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        self.setWindowTitle('Edit Station')
        self.resize(800, 400)
        self.setLayout(layout)

    def save(self):
        station_dict = self.station
        station_dict['station_name'] = self.name_field.text()
        station_dict['station_comment'] = self.comment_field.toPlainText()
        station_dict['length_in'] = self.length_in.value()
        station_dict['azimuth_in'] = self.azimuth_in.value()
        station_dict['depth'] = self.depth.value()
        station_dict['temperature'] = self.temperature.value()
        station_dict['azimuth_out'] = self.azimuth_out.value()
        station_dict['length_out'] = self.length_out.value()

        tree = self.parentWidget()
        model = tree.model()
        model.update_station(data=station_dict, index=tree.selectedIndexes()[0])
        self.close()

    def reset(self):
        station_dict = self.station
        self.name_field.setText(station_dict['station_name'])
        self.comment_field.setText(station_dict['station_comment'])
        self.length_in.setValue(station_dict['length_in'])
        self.azimuth_in.setValue(station_dict['azimuth_in'])
        self.depth.setValue(station_dict['depth'])
        self.temperature.setValue(station_dict['temperature'])
        self.azimuth_out.setValue(station_dict['azimuth_out'])
        self.length_out.setValue(station_dict['length_out'])

    def cancel(self):
        self.close()

