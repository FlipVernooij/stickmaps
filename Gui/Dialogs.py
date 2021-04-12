import pathlib

import PySide6
from PySide6 import QtCore
from PySide6.QtCore import QDateTime, QSysInfo, QSettings, QThread
from PySide6.QtGui import Qt, QPixmap
from PySide6.QtSql import QSqlTableModel
from PySide6.QtWidgets import QErrorMessage, QDialog, QTableView, QHBoxLayout, QMessageBox, QApplication, QFormLayout, \
    QLineEdit, QDateTimeEdit, QTextEdit, QDialogButtonBox, QVBoxLayout, QDoubleSpinBox, QListWidget, QComboBox, QLabel, \
    QPushButton, QFileDialog, QSizePolicy, QTextBrowser

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME, MNEMO_DEVICE_DESCRIPTION, DEBUG, \
    MNEMO_DEVICE_NAME, MNEMO_BAUDRATE, MNEMO_TIMEOUT, MNEMO_CYCLE_COUNT, SURVEY_DIRECTION_IN, SURVEY_DIRECTION_OUT, \
    SQL_DB_LOCATION, GOOGLE_MAPS_SCALING, APPLICATION_CACHE_DIR, APPLICATION_CACHE_MAX_SIZE, APPLICATION_DATA_DIR, \
    APPLICATION_DEFAULT_PROJECT_NAME, APPLICATION_DEFAULT_FILE_NAME, APPLICATION_VERSION, APPLICATION_FILE_EXTENSION, \
    APPLICATION_STARTUP_DIALOG_IMAGE, DOCS_SEARCH_PATHS
from Gui.Delegates.FormElements import DropDown
from Gui.Mixins import FormMixin
from Models.TableModels import SqlManager, ProjectSettings
from Utils.Settings import Preferences

import traceback

from Utils.Storage import SaveFile


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
            QMessageBox.warning(QApplication.instance(), APPLICATION_NAME, message)
        else:
            print(f"ERROR: {message}")


class PreferencesDialog(QDialog, FormMixin):
    FORMS = {
        "General": {
            "fields": {
                "cache_dir": {
                    "label": "Cache directory",
                    "info": f"{APPLICATION_NAME} uses this directory to store cache files.",
                    "form_field": "text_line",
                    "settings_key": "application_cache_dir",
                    "default_value": APPLICATION_CACHE_DIR,
                },
                "cache_size": {
                    "label": "Cache max size in MB",
                    "info": f"The maximum size of your cache directory.",
                    "form_field": "spinner",
                    "min": 50,
                    "max": 1000,
                    "settings_key": "application_cache_max_size",
                    "default_value": APPLICATION_CACHE_MAX_SIZE,
                },
                "dev_mode": {
                    "label": "Enable developer-mode",
                    "info": f"Do not use this unless you know what you are doing, you can break things.",
                    "form_field": "check_box",
                    "settings_key": "debug",
                    "default_value": DEBUG
                }
            }
        },
        "Geolocation & Satellite": {
            "fields": {
                "map_scaling": {
                    "label": "Scaling",
                    "info": "High definition monitors should use 2, low res monitors can use 1 in order to minimize bandwith usage.",
                    "form_field": "combo_box",
                    "options": [
                        "1",
                        "2"
                    ],
                    "settings_key": "google_maps_scaling",
                    "default_value": GOOGLE_MAPS_SCALING
                }
            }
        },
        "Mnemo": {
            "fields": {
                "device_name": {
                    "label": "Device name",
                    "info": "This is the label used as the \"device name\" within your survey.",
                    "form_field": "text_line",
                    "settings_key": "mnemo_device_name",
                    "default_value": MNEMO_DEVICE_NAME
                },
                "read_cycles": {
                  "label": "Read cycles",
                  "info": "The amount of tries we will try to fetch more data from the Mnemo serial connection.",
                    "form_field": "spinner",
                    "min": 10,
                    "max": 100,
                    "settings_key": "mnemo_cycle_count",
                    "default_value": MNEMO_CYCLE_COUNT,
                },
                "device_ident": {
                    "label": "Device ",
                    "info": "The device description to look for when scanning your usb devices for a Mnemo connection.",
                    "form_field": "text_line",
                    "settings_key": "mnemo_device_description",
                    "default_value": MNEMO_DEVICE_DESCRIPTION,
                    "dev_only": True
                },
                "baudrate":{
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
                "timeout": {
                    "label": "Timeout",
                    "info": "Connection timeout",
                    "form_field": "spinner",
                    "min": 0,
                    "max": 10,
                    "settings_key": "mnemo_timeout",
                    "default_value": MNEMO_TIMEOUT,
                    "dev_only": True
                },
            }
        },
        "Info": {
            "fields": {
                "cpu": {
                    "label": "CPU architecture",
                    "form_field": "label",
                    "value": f'{QSysInfo.currentCpuArchitecture()}/{QSysInfo.buildCpuArchitecture()}'
                },
                "threads": {
                    "label": "CPU Thread count",
                    "form_field": "label",
                    "value": f'{QThread.idealThreadCount()}'
                },
                "comp_arch": {
                    "label": "Compiled architecture",
                    "form_field": "label",
                    "value": f'{QSysInfo.buildAbi()}'
                },
                "os": {
                    "label": "Operating system",
                    "form_field": "label",
                    "value": f'{QSysInfo.prettyProductName()}'
                },
                "kernel":{
                    "label": "Kernel version",
                    "form_field": "label",
                    "value": f'{QSysInfo.kernelType()} - {QSysInfo.kernelVersion()}'
                },
                "qt_version":{
                    "label": "QT version",
                    "form_field": "label",
                    "value": f'{QtCore.__version__}'
                },
                "pyside_version":{
                    "label": "PySide version",
                    "form_field": "label",
                    "value": f'{PySide6.__version__}'
                }
            }
        },
        "Debug": {
            "dev_only": True,
            "fields": {
                "db_location": {
                    "label": "Sqlite database location",
                    "info": "Use \":memory:\" to create a fast yet volatile database in RAM.",
                    "form_field": "text_line",
                    "settings_key": "sql_db_location",
                    "default_value": SQL_DB_LOCATION,
                },
                "tmp_dir":
                    {
                    "label": "Tmp directory",
                    "info": f"{APPLICATION_NAME} uses this directory to store temporary files.",
                    "form_field": "text_line",
                    "settings_key": "application_tmp_dir",
                    "default_value": APPLICATION_DATA_DIR,
                },
                "settings_raw": {
                    "label": "QSettings raw data",
                    "form_field": "textarea",
                    "value_from_function": "_settings_as_string"
                },
                "settings_reset": {
                    "label": "Reset settings",
                    "form_field": "button",
                    "button_label": "reset",
                    "action": "_reset_settings"
                }
            }

        }
    }

    def _settings_as_string(self, element: dict) -> str:
        data = Preferences.get_everything()
        r = []
        for key in data:
            r.append(f'\t{key} = {data[key]}')

        return '<br />'.join(r)

    def _reset_settings(self, event):
        response = QMessageBox.question(self, 'Reset ALL settings?', 'You can not undo this, continue?',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if response == QMessageBox.No:
            return

        s = QSettings()
        all_keys = s.allKeys()
        for key in all_keys:
            s.remove(key)

        self.generate_form(self.current_form, self.form_layout)

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
        self.generate_form(self.FORMS[self.current_form], self.form_layout)
        layout.addLayout(self.form_layout)

        o_layout = QVBoxLayout()
        o_layout.addLayout(layout)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Close)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.close)
        o_layout.addWidget(buttons)

        self.setLayout(o_layout)

    def generate_chapters(self):
        while self.list_widget.count() > 0:
            self.list_widget.takeItem(self.list_widget.count() - 1)

        for item in self.FORMS.keys():
            if 'dev_only' in self.FORMS[item] and self.FORMS[item]['dev_only'] is True:
                if Preferences.debug() is False:
                    continue

            self.list_widget.addItem(item)

        self.list_widget.itemClicked.connect(self.chapter_clicked)

    def chapter_clicked(self, event):
        if self.form_changed is True:
            response = QMessageBox.question(self, 'Ignore unsaved changes?', 'You have unsaved changes, continue?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.No:
                return

        self.form_changed = False
        self.current_form = event.text()
        self.generate_form(self.FORMS[self.current_form], self.form_layout)

    def save(self):
        for field in self.FORMS[self.current_form]['fields'].values():
            if 'settings_key' in field and 'form_element' in field:
                Preferences.set(field['settings_key'], self.get_field_value(field))

        self.generate_chapters()
        self.main_window.toggle_debug_console(Preferences.debug())

        self.form_changed = False

    def close(self, event=None):
        if self.form_changed is True:
            response = QMessageBox.question(self, 'Ignore unsaved changes?', 'You have unsaved changes, continue?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if response == QMessageBox.No:
                return

        super().close()


class DocumentationDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        browser = QTextBrowser(self)

        browser.setOpenLinks(True)
        browser.setSearchPaths(DOCS_SEARCH_PATHS)
        browser.setSource(f'index.html')

        layout = QVBoxLayout(self)
        layout.addWidget(browser)
        self.setLayout(layout)
        self.show()


class NewProjectDialog(QDialog, FormMixin):

    FORM = {
        "title": "Create new project",
        "fields": {
                    "project_name": {
                        "label": "Project name",
                        "form_field": "text_line",
                        "default_value": APPLICATION_DEFAULT_PROJECT_NAME
                    },
                    "file_name": {
                        "label": "File name",
                        "form_field": "save_file_path",
                        "default_value": APPLICATION_DEFAULT_FILE_NAME
                    },
                    "spacer": {
                        "form_field": "spacer",
                    },
                    "use_geo": {
                        "label": "Use geo-location",
                        "form_field": "check_box",
                        "field_changed": "_toggle_geo_location",
                        "default_value": False
                    },
                    "lat_lng": {
                        "label": "Latitude / Longitude",
                        "form_field": "group_field",
                        "fields": {
                            "latitude": {
                                "form_field": "spinner",
                                "is_float": True,
                                "placeholder": "- Latitude - (00.0000000)",
                                "disabled": True,
                                "decimals": 14,
                                'min': -90,
                                'max': 90
                            },
                            "longitude": {
                                "form_field": "spinner",
                                "is_float": True,
                                "placeholder": "- Longitude - (00.0000000)",
                                "disabled": True,
                                "decimals": 14,
                                'min': -180,
                                'max': 180,
                            }
                        },
                        "default_value": False
                    }
            }
    }

    def __init__(self, parent, startup_widget=None):
        super().__init__(parent)
        self.parent = parent
        self.startup_widget = startup_widget
        self.setWindowTitle(f'Create new project')
        self.setFixedSize(800, 400)
        self.parent.disable_ui()


        form_layout = QFormLayout()
        self.generate_form(self.FORM, form_layout)
        self.form_layout = form_layout


        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.create_project)
        buttons.rejected.connect(self.cancel)
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(buttons)
        self.setLayout(main_layout)

    def _toggle_geo_location(self):
        toggle = self.FORM['fields']['use_geo']['form_element']
        lat = self.FORM['fields']['lat_lng']['fields']['latitude']['form_element']
        lng = self.FORM['fields']['lat_lng']['fields']['longitude']['form_element']

        lat.setEnabled(toggle.isChecked())
        lng.setEnabled(toggle.isChecked())

    def create_project(self):
        file_name = self.get_field_value(self.FORM['fields']['file_name'])
        project_name = self.get_field_value(self.FORM['fields']['project_name'])
        if bool(self.get_field_value(self.FORM['fields']['use_geo'])) is True:
            latitude = self.get_field_value(self.FORM['fields']['lat_lng']['fields']['latitude'])
            longitude = self.get_field_value(self.FORM['fields']['lat_lng']['fields']['longitude'])
        else:
            latitude = None
            longitude = None

        save = SaveFile(self.parent, file_name)
        save.create_new_project(project_name, latitude, longitude)
        self.close()

    def cancel(self):
        return self.close()

    def closeEvent(self, event) -> None:
        project = SqlManager().factor(ProjectSettings).get()
        if project is None:
            if self.startup_widget is not None:
                event.accept()
                self.startup_widget.show()
                return
            QMessageBox.information(self.parent, "You have to create a project", "Please create a project before exiting this wizard")
            event.ignore()
            return

        self.parent.enable_ui()
        event.accept()


class OpenProjectDialog(QFileDialog):

    def __init__(self, parent, startup_widget=None):
        super().__init__(parent)
        self.parent = parent
        self.startup_widget = startup_widget
        self.setWindowTitle(f'Open project')
        self.setFixedSize(800, 400)
        self.settings = QSettings()

        try:
            file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
            file_ident = f'{APPLICATION_NAME} {file_regex}'
            #self.setDisabled(path)
            self.setWindowTitle('Create file')
            self.setFilter(self.filter())
            self.setDefaultSuffix(APPLICATION_FILE_EXTENSION)
            self.setAcceptMode(QFileDialog.AcceptOpen)
            self.setNameFilters([file_ident])
            self.setDirectory(self.settings.value('SaveFile/last_path', str(pathlib.Path.home())))
            self.setOption(QFileDialog.DontUseNativeDialog)
            self.setWindowTitle('Open project')

            self.fileSelected.connect(self.open)
        except Exception as err_mesg:
            ErrorDialog.show_error_key(self.parent, str(err_mesg))

    def open(self, file):
        save = SaveFile(self.parent, file)
        save.open_project()

        self.close()

    def reject(self):
        project = SqlManager().factor(ProjectSettings).get()
        if project is None:
            if self.startup_widget is not None:
                self.startup_widget.show()
                self.close()
                return

            QMessageBox.information(self.parent, "You have to create a project",
                                    "Please create a project before exiting this wizard")
            return

        self.parent.enable_ui()

    def closeEvent(self, event) -> None:
        project = SqlManager().factor(ProjectSettings).get()
        if project is None:
            if self.startup_widget is not None:
                event.accept()
                self.startup_widget.show()
                return

            QMessageBox.information(self.parent, "You have to create a project",
                                    "Please create a project before exiting this wizard")
            event.ignore()
            return

        self.parent.enable_ui()
        event.accept()


class StartupWidget(QDialog):

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.parent.disable_ui()
        self.setWindowTitle(f'Welcome!')
        self.setFixedSize(300, 200)

        pixmap = QPixmap(APPLICATION_STARTUP_DIALOG_IMAGE)
        logo = QLabel(self)
        logo.setPixmap(pixmap)
        logo.setAlignment(Qt.AlignCenter)
        version = QLabel(f'{APPLICATION_NAME} v: {APPLICATION_VERSION}')
        version.setAlignment(Qt.AlignCenter)

        new_project = QPushButton("Create new project")
        open_project = QPushButton("Open existing project")
        new_project.clicked.connect(self.show_new_project)
        open_project.clicked.connect(self.show_open_project)
        new_project.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        open_project.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout()
        layout.addSpacing(10)
        layout.addWidget(logo)
        layout.addWidget(version)
        layout.addSpacing(20)
        layout.addStretch()
        layout.addWidget(open_project)

        layout.addWidget(new_project)
        layout.addStretch()
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)

    def closeEvent(self, event) -> None:
        project = SqlManager().factor(ProjectSettings).get()
        if project is None:
            QMessageBox.information(self.parent, "You have to create a project",
                                    "Please create a project before exiting this wizard")
            event.ignore()
            return

        self.parent.enable_ui()
        event.accept()

    def show_new_project(self):
        d = NewProjectDialog(self.parent, self)
        d.show()
        self.hide()


    def show_open_project(self):
        d = OpenProjectDialog(self.parent, self)
        d.show()
        self.hide()


class EditSurveysDialog(QDialog):

    def __init__(self, parent, selected_item):
        super().__init__(parent)
        self.item = selected_item
        model = selected_item.model()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.select()

        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.sortByColumn(0, Qt.AscendingOrder)
        view.setSelectionMode(QTableView.NoSelection)

        model.set_column_widths(view)

        view.horizontalHeader().setStretchLastSection(True)



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

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.item.update_children()
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
        self.item = item

        self.survey = item.model().get(item.survey_id())

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
        self.item.model().update(survey_dict, survey_dict['survey_id'])
        self.item.update(survey_dict['survey_name'])
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


class EditLinesDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.survey_id = item.survey_id()
        self.item = item
        self.setWindowTitle('Edit Lines')
        self.resize(800, 400)

        model = item.child_model()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'survey_id={self.survey_id}')

        model.select()

        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.sortByColumn(0, Qt.AscendingOrder)
        view.setSelectionMode(QTableView.NoSelection)
        model.set_column_widths(view)

        view.horizontalHeader().setStretchLastSection(True)

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
        self.item.update_children()
        self.close()

    def reset(self):
        table = self.table_view
        model = table.model()

        model.revertAll()

    def cancel(self):
        self.close()


class EditLineDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent)
        self.line = item.model().get(item.line_id())
        self.item = item

        layout = QFormLayout()
        layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.id_field = QLineEdit(str(self.line['line_reference_id']))
        self.id_field.setClearButtonEnabled(False)
        self.id_field.setDisabled(True)
        layout.addRow('&Line id', self.id_field)

        self.name_field = QLineEdit(self.line['line_name'])
        self.name_field.setClearButtonEnabled(True)
        layout.addRow('&Name', self.name_field)

        self.direction_field = QComboBox(self)
        self.direction_field.addItem(SURVEY_DIRECTION_IN)
        self.direction_field.addItem(SURVEY_DIRECTION_OUT)
        self.direction_field.setCurrentText(self.line['direction'])
        layout.addRow('&Direction', self.direction_field)

        self.comment_field = QTextEdit(self.line['line_comment'])
        layout.addRow('&Comment', self.comment_field)

        buttons = QDialogButtonBox(QDialogButtonBox.Reset | QDialogButtonBox.Cancel | QDialogButtonBox.Save)
        layout.addRow(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        self.setWindowTitle('Edit Line')
        self.resize(800, 400)
        self.setLayout(layout)

    def save(self):
        line_dict = self.line
        line_dict['line_name'] = self.name_field.text()
        line_dict['line_comment'] = self.comment_field.toPlainText()
        line_dict['direction'] = self.direction_field.currentText()

        tree = self.parentWidget()
        self.item.model().update(line_dict, line_dict['line_id'])
        self.item.update(line_dict['line_name'])
        self.close()

    def reset(self):
        line_dict = self.line
        self.name_field.setText(line_dict['line_name'])
        self.comment_field.setText(line_dict['line_comment'])

    def cancel(self):
        self.close()


class EditStationsDialog(QDialog):

    def __init__(self, parent, item):
        super().__init__(parent.main_window)
        self.tree_view = parent
        self.line_id = item.line_id()
        self.item = item
        self.setWindowTitle('Edit stations')
        self.resize(800, 400)



        model = item.child_model()
        model.select()
        model.setEditStrategy(QSqlTableModel.OnManualSubmit)
        model.setFilter(f'line_id={self.line_id}')


        view = QTableView(self)
        view.setModel(model)
        view.setAlternatingRowColors(True)
        view.setSortingEnabled(True)
        view.sortByColumn(0, Qt.AscendingOrder)
        view.setSelectionMode(QTableView.NoSelection)
        model.set_column_widths(view)



        layout = QVBoxLayout()
        layout.addWidget(view)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Save | QDialogButtonBox.Reset)
        layout.addWidget(buttons)

        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.cancel)
        buttons.button(QDialogButtonBox.Reset).clicked.connect(self.reset)

        view.horizontalHeader().setStretchLastSection(True)

        view.resizeColumnsToContents()

        self.table_view = view
        self.setLayout(layout)

    def save(self):
        table = self.table_view
        model = table.model()
        model.submitAll()
        self.item.update_children()
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
        self.station = item.model().get(item.station_id())
        self.item = item

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
        station_dict['azimuth_out'] = self.azimuth_out.value()
        station_dict['length_out'] = self.length_out.value()

        self.item.model().update(station_dict, station_dict['station_id'])
        self.item.update(station_dict['station_name'])
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

