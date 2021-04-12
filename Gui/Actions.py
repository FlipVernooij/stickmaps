import logging
import os
import pathlib

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QIcon

from PySide6.QtWidgets import QFileDialog, QTreeView, QMenu, QMessageBox, QDialog, QToolBar

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME, APPLICATION_FILE_EXTENSION, \
    MAIN_WINDOW_TITLE, MNEMO_BAUDRATE, MNEMO_TIMEOUT
from Config.Icons import ICON_TOGGLE_SATELLITE
from Config.KeyboardShortcuts import KEY_IMPORT_MNEMO_CONNECT, KEY_IMPORT_MNEMO_DUMP_FILE, KEY_QUIT_APPLICATION, \
    KEY_SAVE, KEY_SAVE_AS, KEY_OPEN, KEY_NEW, KEY_IMPORT_MNEMO_DUMP, KEY_PREFERENCES, KEY_TOGGLE_SATELLITE
from Gui.Dialogs import ErrorDialog, EditSurveyDialog, EditLinesDialog, EditLineDialog, EditStationsDialog, \
    EditStationDialog, PreferencesDialog, NewProjectDialog, OpenProjectDialog, DocumentationDialog
from Gui.Dialogs import EditSurveysDialog
from Importers.Mnemo import MnemoImporter
from Utils.Settings import Preferences
from Utils.Storage import SaveFile
from Workers.Mixins import ThreadWithProgressBar


class GlobalActions(ThreadWithProgressBar):

    THREAD_MNEMO_CONNECTION = 'mnemo_connection'

    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent = parent_window

### File menu
    def new(self):
        action = QAction('New', self.parent)
        action.setShortcut(KEY_NEW)
        action.triggered.connect(lambda: self.new_callback())
        return action

    def new_callback(self):
        SaveFile(self.parent).check_if_save_required()
        dialog = NewProjectDialog(self.parent)
        dialog.show()

    def open(self):
        action = QAction('Open', self.parent)
        action.setShortcut(KEY_OPEN)
        action.triggered.connect(lambda: self.open_callback())

        return action

    def open_callback(self):
        SaveFile(self.parent).check_if_save_required()

        dialog = OpenProjectDialog(self.parent)
        dialog.show()

    def save(self):
        action = QAction('Save', self.parent)
        action.setShortcut(KEY_SAVE)
        action.triggered.connect(lambda: self.save_callback())
        return action

    def save_callback(self):
        settings = QSettings()
        file_name = settings.value('SaveFile/current_file_name', None)
        if file_name is not None:
            save = SaveFile(self.parent, file_name)
            save.save_to_file()
            self.current_file_name = file_name
            self.parent.statusBar().showMessage('File saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)
            settings.setValue('SaveFile/is_changed', False)
        else:
            self.save_as_callback()

    def save_as(self):
        action = QAction('Save as', self.parent)
        action.setShortcut(KEY_SAVE_AS)
        action.triggered.connect(lambda: self.save_as_callback())
        return action

    def save_as_callback(self):
        settings = QSettings()
        self.parent.statusBar().showMessage('Saving file, do not exit.')
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
            save = SaveFile(self.parent, file_name)
            save.save_to_file()
            self.current_file_name = file_name
            self.parent.statusBar().showMessage('File saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

            settings.setValue('SaveFile/is_changed', False)
            settings.setValue('SaveFile/last_path', os.path.dirname(file_name))
            self._update_window_title(file_name)
        else:
            self.parent.statusBar().showMessage('File NOT saved.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

    def preferences(self):
        action = QAction('Preferences', self.parent)
        action.setMenuRole(QAction.PreferencesRole)
        action.setShortcut(KEY_PREFERENCES)
        action.triggered.connect(lambda: self.preferences_callback())
        return action

    def preferences_callback(self):
        prefs = PreferencesDialog(self.parent)
        prefs.show()

    def exit_application(self):
        action = QAction('Exit', self.parent)
        action.setShortcut(KEY_QUIT_APPLICATION)
        action.setMenuRole(QAction.QuitRole)

        action.triggered.connect(self.parent.close)
        return action

### Import menu
    def mnemo_connect_to(self):
        action = QAction('Import from Mnemo', self.parent)
        action.setShortcut(KEY_IMPORT_MNEMO_CONNECT)
        action.triggered.connect(lambda: self.mnemo_connect_to_callback())
        return action

    def mnemo_connect_to_callback(self):
        self.parent.statusBar().showMessage('Mnemo import in progress', MAIN_WINDOW_STATUSBAR_TIMEOUT)
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
        action = QAction('Backup Mnemo (*.dmp file)', self.parent)
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
            self.parent.statusBar().showMessage('Mnemo backup in progress', MAIN_WINDOW_STATUSBAR_TIMEOUT)

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
        action = QAction('Load Mnemo *.dmp file', self.parent)
        action.setShortcut(KEY_IMPORT_MNEMO_DUMP_FILE)
        action.triggered.connect(lambda: self.mnemo_load_dump_file_callback())
        return action

    def mnemo_load_dump_file_callback(self):
        try:
            file = QFileDialog(self.parent)
            settings = QSettings()
            options = file.Options() | file.DontUseNativeDialog

            file.setOptions(options)
            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilters(['Mnemo dump file (*.dmp)', 'All files (*)'])
            file.setDirectory(settings.value('SaveFile/last_path_mnemo_import', str(pathlib.Path.home())))

            if file.exec() == QFileDialog.Accepted:
                file_name = file.selectedFiles()[0]
                settings.setValue('SaveFile/last_path_mnemo_import', os.path.dirname(file_name))
                self.parent.statusBar().showMessage('Loading Mnemo *.dmp file.', MAIN_WINDOW_STATUSBAR_TIMEOUT)
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
            ErrorDialog.show_error_key(self.parent, str(err_mesg))

    def _disable_mnemo_actions(self):
        menubar = self.parent.menuBar()
        menubar.actions()[2].setEnabled(False)

    def _enable_mnemo_actions(self):
        menubar = self.parent.menuBar()
        menubar.actions()[2].setEnabled(True)

    def _update_window_title(self, file_name: str, max_length: int = 150):
        if len(file_name) > max_length:
            file_name = f'...{file_name[len(file_name) - (max_length-3)::]}'
        self.parent.setWindowTitle(f'{MAIN_WINDOW_TITLE} - {file_name}')

## Help menu

    def about_qt(self):
        action = QAction('About QT', self.parent)
        action.triggered.connect(lambda: self.about_qt_callback())
        return action

    def about_qt_callback(self):
        QMessageBox.aboutQt(self.parent, 'About QT')

    def documentation(self):
        action = QAction('Documentation', self.parent)
        action.triggered.connect(lambda: self.documentation_callback())
        return action

    def documentation_callback(self):
        docs = DocumentationDialog(self.parent)
        docs.show()

class TreeActions:

    def __init__(self, tree_view: QTreeView, context_menu: QMenu):
        self.context_menu = context_menu
        self.tree_view = tree_view
        self.remove_alert = None

    def get_selected_item(self):
        index = self.tree_view.selectedIndexes()[0]
        return index.model().itemFromIndex(index)

    def edit_surveys(self):
        action = QAction('Edit surveys', self.context_menu)
        action.triggered.connect(lambda: self.edit_surveys_callback())
        return action

    def edit_surveys_callback(self):
        dialog = EditSurveysDialog(self.tree_view, self.get_selected_item())
        dialog.show()

    def remove_surveys(self):
        action = QAction('Delete surveys', self.context_menu)
        action.triggered.connect(lambda: self.remove_surveys_callback())
        return action

    def remove_surveys_callback(self):
        msg = QMessageBox(QMessageBox.Warning, "Delete Surveys", "<h3>Are you sure?</h3><p>Deleting all Surveys will delete all containing Lines and Points.</p>", QMessageBox.Ok | QMessageBox.Cancel)
        self.remove_alert = msg
        if msg.exec_() == QMessageBox.Ok:
            item = self.get_selected_item()
            num_rows = item.model().flush()
            item.delete_children()
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed surveys, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

    def edit_survey(self):
        action = QAction('edit survey', self.context_menu)
        action.triggered.connect(lambda: self.edit_survey_callback())
        return action

    def edit_survey_callback(self):
        form = EditSurveyDialog(self.tree_view, self.get_selected_item())
        form.show()

    def remove_survey(self):
        action = QAction('delete survey', self.context_menu)
        action.triggered.connect(lambda: self.remove_survey_callback())
        return action

    def remove_survey_callback(self):
        msg = QMessageBox(
            QMessageBox.Warning,
            "Delete Survey",
            "<h3>Are you sure?</h3><p>Deleting this Survey will delete all containing Lines and Points.</p>",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        self.remove_alert = msg
        if msg.exec_() == QMessageBox.Ok:
            item = self.get_selected_item()
            num_rows = item.model().delete(item.survey_id())
            item.remove()
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed survey, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

    def edit_lines(self):
        action = QAction('edit lines', self.context_menu)
        action.triggered.connect(lambda: self.edit_lines_callback())
        return action

    def edit_lines_callback(self):
        dialog = EditLinesDialog(self.tree_view, self.get_selected_item())
        dialog.show()

    def remove_empty_lines(self):
        action = QAction('remove empty lines', self.context_menu)
        action.triggered.connect(lambda: self.remove_empty_lines_callback())
        return action

    def remove_empty_lines_callback(self):
        item = self.get_selected_item()
        c = item.child_model().flush_empty(item.survey_id())
        item.update_children()
        self.tree_view.setCurrentIndex(item.index())
        self.tree_view.main_window.statusBar().showMessage(f'Removed {c} empty lines from survey', MAIN_WINDOW_STATUSBAR_TIMEOUT)

    def edit_line(self):
        action = QAction('edit line', self.context_menu)
        action.triggered.connect(lambda: self.edit_line_callback())
        return action

    def edit_line_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        form = EditLineDialog(self.tree_view, index.model().itemFromIndex(index))
        form.show()

    def remove_line(self):
        action = QAction('delete line', self.context_menu)
        action.triggered.connect(lambda: self.remove_line_callback())
        return action

    def remove_line_callback(self):
        msg = QMessageBox(
            QMessageBox.Warning,
            "Delete Line",
            "<h3>Are you sure?</h3><p>Deleting this Line will delete all containing Points.</p>",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        self.remove_alert = msg
        if msg.exec_() == QMessageBox.Ok:
            item = self.get_selected_item()
            num_rows = item.model().delete(item.line_id())
            item.remove()
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed line, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

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
        msg = QMessageBox(
            QMessageBox.Warning,
            "Delete Station",
            "<h3>Are you sure?</h3><p>Deleting this Point will require you to verify connected stations</p>",
            QMessageBox.Ok | QMessageBox.Cancel
        )
        self.remove_alert = msg
        if msg.exec_() == QMessageBox.Ok:
            item = self.get_selected_item()
            num_rows = item.model().delete(item.station_id())
            item.remove()
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed station, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

class MapToolbarActions:

    def __init__(self, toolbar: QToolBar, map_view):
        self.map_view = map_view
        self.toolbar = toolbar

    def toggle_satellite(self):
        action = QAction(QIcon(ICON_TOGGLE_SATELLITE), 'toggle satellite', self.toolbar)
        action.setShortcut(KEY_TOGGLE_SATELLITE)
        action.triggered.connect(lambda: self.toggle_satellite_callback())
        return action

    def toggle_satellite_callback(self):
        logging.getLogger().warning('sending s_toggle_satellite signal')
        self.map_view.s_toggle_satellite.emit(None)
