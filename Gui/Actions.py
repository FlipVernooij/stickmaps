import os
import pathlib

from PySide6.QtCore import QSettings, QObject, QThread
from PySide6.QtGui import QAction

from PySide6.QtWidgets import QFileDialog, QTreeView, QMenu, QMessageBox, QDialog, QProgressDialog

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME, APPLICATION_FILE_EXTENSION, \
    MAIN_WINDOW_TITLE, MNEMO_BAUDRATE, MNEMO_TIMEOUT
from Config.KeyboardShortcuts import KEY_IMPORT_MNEMO_CONNECT, KEY_IMPORT_MNEMO_DUMP_FILE, KEY_QUIT_APPLICATION, \
    KEY_SAVE, KEY_SAVE_AS, KEY_OPEN, KEY_NEW, KEY_IMPORT_MNEMO_DUMP, KEY_PREFERENCES
from Gui.Dialogs import ErrorDialog, EditSurveyDialog, EditSectionsDialog, EditSectionDialog, EditStationsDialog, \
    EditStationDialog, PreferencesDialog
from Gui.Dialogs import EditSurveysDialog
from Importers.Mnemo import MnemoImporter
from Utils.Settings import Preferences
from Utils.Storage import SurveyData
from Workers.Mixins import ThreadWithProgressBar


class GlobalActions(ThreadWithProgressBar):

    THREAD_MNEMO_CONNECTION = 'mnemo_connection'

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window

    def new(self):
        action = QAction('New', self.parent_window)
        action.setShortcut(KEY_NEW)
        action.triggered.connect(lambda: self.new_callback())
        return action

    def new_callback(self):
        self._check_if_save_required()
        save = SurveyData('')
        save.load_new()
        self.parent_window.tree_view.model().reload_model()
        self._update_window_title('*new')

        settings = QSettings()
        settings.setValue('SaveFile/is_changed', False)
        settings.setValue('SaveFile/current_file_name', None)

    def open(self):
        action = QAction('Open', self.parent_window)
        action.setShortcut(KEY_OPEN)
        action.triggered.connect(lambda: self.open_callback())

        return action

    def open_callback(self):
        self._check_if_save_required()
        settings = QSettings()
        path = settings.value('SaveFile/last_path', str(pathlib.Path.home()))
        try:
            file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
            file_ident = f'{APPLICATION_NAME} {file_regex}'
            name = QFileDialog.getOpenFileName(
                parent=self.parent_window,
                caption="Open file",
                dir=path,
                filter=file_ident,
                selectedFilter=file_ident,
                options=QFileDialog.Options() | QFileDialog.DontUseNativeDialog
            )

            if not name[0]:
                return

            name = name[0]
            save = SurveyData(name)
            save.load_from_file()
            self.parent_window.tree_view.model().reload_model()
            self._update_window_title(name)

            settings.setValue('SaveFile/is_changed', False)
            settings.setValue('SaveFile/last_path', os.path.dirname(name))
            settings.setValue('SaveFile/current_file_name', name)
        except Exception as err_mesg:
            ErrorDialog.show_error_key(self.parent_window, str(err_mesg))

    def save(self):
        action = QAction('Save', self.parent_window)
        action.setShortcut(KEY_SAVE)
        action.triggered.connect(lambda: self.save_callback())
        return action

    def save_callback(self):
        settings = QSettings()
        file_name = settings.value('SaveFile/current_file_name', None)
        if file_name is not None:
            save = SurveyData(file_name)
            save.save_to_file()
            self.current_file_name = file_name
            self.parent_window.statusBar().showMessage('File saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)
            settings = QSettings()
            settings.setValue('SaveFile/is_changed', False)
        else:
            self.save_as_callback()

    def save_as(self):
        action = QAction('Save as', self.parent_window)
        action.setShortcut(KEY_SAVE_AS)
        action.triggered.connect(lambda: self.save_as_callback())
        return action

    def save_as_callback(self):
        settings = QSettings()
        self.parent_window.statusBar().showMessage('Saving file, do not exit.')
        file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
        file_ident = f'{APPLICATION_NAME} {file_regex}'
        dialog = QFileDialog()
        dialog.setWindowTitle('Save file')
        dialog.setFilter(dialog.filter())
        dialog.setDefaultSuffix(APPLICATION_FILE_EXTENSION)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters([file_ident])
        dialog.setDirectory(settings.value('SaveFile/last_path', str(pathlib.Path.home())))
        dialog.setOption(QFileDialog.DontUseNativeDialog)
        if dialog.exec_() == QDialog.Accepted:
            file_name = dialog.selectedFiles()[0]
            if file_name[-4:] != f'.{APPLICATION_FILE_EXTENSION}':
                file_name = f'{file_name}.{APPLICATION_FILE_EXTENSION}'
            save = SurveyData(file_name)
            save.save_to_file()
            self.current_file_name = file_name
            self.parent_window.statusBar().showMessage('File saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

            settings.setValue('SaveFile/is_changed', False)
            settings.setValue('SaveFile/last_path', os.path.dirname(file_name))
            self._update_window_title(file_name)
        else:
            self.parent_window.statusBar().showMessage('File NOT saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

    def preferences(self):
        action = QAction('Preferences', self.parent_window)
        action.setMenuRole(QAction.PreferencesRole)
        action.setShortcut(KEY_PREFERENCES)
        action.triggered.connect(lambda: self.preferences_callback())
        return action

    def preferences_callback(self):
        prefs = PreferencesDialog(self.parent_window)
        prefs.show()

    def exit_application(self):
        action = QAction('Exit', self.parent_window)
        action.setShortcut(KEY_QUIT_APPLICATION)
        action.setMenuRole(QAction.QuitRole)

        action.triggered.connect(self.parent_window.close)
        return action

### Import menu
    def mnemo_connect_to(self):
        action = QAction('Import from Mnemo', self.parent_window)
        action.setShortcut(KEY_IMPORT_MNEMO_CONNECT)
        action.triggered.connect(lambda: self.mnemo_connect_to_callback())
        return action

    def mnemo_connect_to_callback(self):
        self.parent_window.statusBar().showMessage('Mnemo import in progress', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        self._disable_mnemo_actions()
        mnemo_dump = MnemoImporter(
            baudrate=int(Preferences.get('mnemo_baudrate', MNEMO_BAUDRATE)),
            timeout=int(Preferences.get('mnemo_timeout', MNEMO_TIMEOUT)),
            thread_action=MnemoImporter.ACTION_READ_DEVICE
        )
        self.worker_create_thread(
            thread_object=mnemo_dump,
            progress_params={"title": "Mnemo import"},
            on_finish=self._enable_mnemo_actions
        )

        self.worker_start(self.THREAD_MNEMO_CONNECTION)

    def mnemo_dump(self):
        action = QAction('Backup Mnemo (*.dmp file)', self.parent_window)
        action.setShortcut(KEY_IMPORT_MNEMO_DUMP)
        action.triggered.connect(lambda: self.mnemo_dump_callback())
        return action

    def mnemo_dump_callback(self):
        file_regex = f'(*.dmp)'
        file_ident = f'Mnemo dump file {file_regex}'
        settings = QSettings()
        dialog = QFileDialog()
        dialog.setWindowTitle('Save file')
        dialog.setFilter(dialog.filter())
        dialog.setDefaultSuffix('dmp')
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters([file_ident])
        dialog.setDirectory(settings.value('SaveFile/last_path', str(pathlib.Path.home())))
        dialog.setOption(QFileDialog.DontUseNativeDialog)
        if dialog.exec_() == QDialog.Accepted:
            file_name = dialog.selectedFiles()[0]
            if file_name[-4:] != f'.dmp':
                file_name = f'{file_name}.dmp'
            self.parent_window.statusBar().showMessage('Mnemo backup in progress', MAIN_WINDOW_STATUSBAR_TIMEOUT)

            mnemo_dump = MnemoImporter(
                baudrate=int(Preferences.get('mnemo_baudrate', MNEMO_BAUDRATE)),
                timeout=int(Preferences.get('mnemo_timeout', MNEMO_TIMEOUT)),
                thread_action=MnemoImporter.ACTION_WRITE_DUMP,
                out_file=file_name
            )
            self.worker_create_thread(
                thread_object=mnemo_dump,
                progress_params={"title": "Mnemo backup"}
            )

            self.worker_start(self.THREAD_MNEMO_CONNECTION)

    def mnemo_load_dump_file(self):
        action = QAction('Load Mnemo *.dmp file', self.parent_window)
        action.setShortcut(KEY_IMPORT_MNEMO_DUMP_FILE)
        action.triggered.connect(lambda: self.mnemo_load_dump_file_callback())
        return action

    def mnemo_load_dump_file_callback(self):
        try:
            file = QFileDialog(self.parent_window)
            settings = QSettings()
            options = file.Options() | file.DontUseNativeDialog

            file.setOptions(options)
            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilters(['Mnemo dump file (*.dmp)', 'All files (*)'])
            file.setDirectory(settings.value('SaveFile/last_path_mnemo_import', str(pathlib.Path.home())))

            if file.exec() == QFileDialog.Accepted:
                file_name = file.selectedFiles()[0]
                settings.setValue('SaveFile/last_path_mnemo_import', os.path.dirname(file_name))
                self.parent_window.statusBar().showMessage('Loading Mnemo *.dmp file.', MAIN_WINDOW_STATUSBAR_TIMEOUT)
                mnemo = MnemoImporter(
                    thread_action=MnemoImporter.ACTION_READ_DUMP,
                    in_file=file_name
                )
                self.worker_create_thread(
                    thread_object=mnemo,
                    progress_params={"title": "Mnemo load *.dmp file"}
                )

                self.worker_start(self.THREAD_MNEMO_CONNECTION)
        except Exception as err_mesg:
            ErrorDialog.show_error_key(self.parent_window, str(err_mesg))

    def _disable_mnemo_actions(self):
        menubar = self.parent_window.menuBar()
        menubar.actions()[2].setEnabled(False)

    def _enable_mnemo_actions(self):
        menubar = self.parent_window.menuBar()
        menubar.actions()[2].setEnabled(True)

    def edit_survey(self):
        action = QAction('Edit surveys', self.parent_window)
        action.triggered.connect(lambda: self.edit_survey_callback())
        return action

    def edit_survey_callback(self):
        EditSurveysDialog.display(self.parent_window)

    def _check_if_save_required(self):
        settings = QSettings()
        if settings.value('SaveFile/is_changed', False) is True:
            response = QMessageBox.question(self.parent_window, 'Save current changes?',
                                            'You have a file with pending changes. \n Do you want to save changes?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if response == QMessageBox.Yes:
                self.save_callback()

    def _update_window_title(self, file_name: str, max_length: int = 150):
        if len(file_name) > max_length:
            file_name = f'...{file_name[len(file_name) - (max_length-3)::]}'
        self.parent_window.setWindowTitle(f'{MAIN_WINDOW_TITLE} - {file_name}')


class TreeActions:

    def __init__(self, tree_view: QTreeView, context_menu: QMenu):
        self.context_menu = context_menu
        self.tree_view = tree_view
        self.remove_alert = None

    def edit_survey(self):
        action = QAction('edit survey', self.context_menu)
        action.triggered.connect(lambda: self.edit_survey_callback())
        return action

    def edit_survey_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        form = EditSurveyDialog(self.tree_view, index.model().itemFromIndex(index))
        form.show()

    def remove_survey(self):
        action = QAction('delete survey', self.context_menu)
        action.triggered.connect(lambda: self.remove_survey_callback())
        return action

    def remove_survey_callback(self):
        msg = QMessageBox()
        self.remove_alert = msg
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Are you sure?")
        msg.setInformativeText("Deleting this Survey will delete all containing Sections and Points.")
        msg.setWindowTitle("Delete Survey")
        #msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if msg.exec_() == QMessageBox.Ok:
            index = self.tree_view.selectedIndexes()[0]
            item = index.model().itemFromIndex(index)
            num_rows = item.model().delete_survey(item)
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed survey, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

    def edit_sections(self):
        action = QAction('edit sections', self.context_menu)
        action.triggered.connect(lambda: self.edit_sections_callback())
        return action

    def edit_sections_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        item = index.model().itemFromIndex(index)
        dialog = EditSectionsDialog(self.tree_view, item)
        dialog.show()

    def edit_section(self):
        action = QAction('edit section', self.context_menu)
        action.triggered.connect(lambda: self.edit_section_callback())
        return action

    def edit_section_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        form = EditSectionDialog(self.tree_view, index.model().itemFromIndex(index))
        form.show()

    def remove_section(self):
        action = QAction('delete section', self.context_menu)
        action.triggered.connect(lambda: self.remove_section_callback())
        return action

    def remove_section_callback(self):
        msg = QMessageBox()
        self.remove_alert = msg
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Are you sure?")
        msg.setInformativeText("Deleting this Section will delete all containing station too.")
        msg.setWindowTitle("Delete Section")
        #msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if msg.exec_() == QMessageBox.Ok:
            index = self.tree_view.selectedIndexes()[0]
            item = index.model().itemFromIndex(index)
            num_rows = item.model().delete_section(item)
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed section, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

    def edit_stations(self):
        action = QAction('edit stations', self.context_menu)
        action.triggered.connect(lambda: self.edit_stations_callback())
        return action

    def edit_stations_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        item = index.model().itemFromIndex(index)
        dialog = EditStationsDialog(self.tree_view, item)
        dialog.show()

    def edit_station(self):
        action = QAction('edit station', self.context_menu)
        action.triggered.connect(lambda: self.edit_station_callback())
        return action

    def edit_station_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        form = EditStationDialog(self.tree_view, index.model().itemFromIndex(index))
        form.show()

    def remove_station(self):
        action = QAction('delete station', self.context_menu)
        action.triggered.connect(lambda: self.remove_station_callback())
        return action

    def remove_station_callback(self):
        msg = QMessageBox()
        self.remove_alert = msg
        msg.setIcon(QMessageBox.Warning)

        msg.setText("Are you sure?")
        msg.setInformativeText("Deleting this Station requires you too verify surrounding stations.")
        msg.setWindowTitle("Delete Station")
        #msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if msg.exec_() == QMessageBox.Ok:
            index = self.tree_view.selectedIndexes()[0]
            item = index.model().itemFromIndex(index)
            num_rows = item.model().delete_station(item)
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed station, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

