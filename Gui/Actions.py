import pathlib

from PySide6.QtCore import QDir
from PySide6.QtGui import QAction

from PySide6.QtWidgets import QFileDialog, QTreeView, QMenu, QMessageBox, QDialog

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, APPLICATION_NAME, APPLICATION_FILE_EXTENSION
from Config.KeyboardShortcuts import KEY_IMPORT_MNEMO_CONNECT, KEY_IMPORT_MNEMO_DUMP_FILE, KEY_QUIT_APPLICATION, \
    KEY_SAVE, KEY_SAVE_AS, KEY_OPEN
from Gui.Dialogs import ErrorDialog, EditSurveyDialog, EditSectionsDialog, EditSectionDialog, EditPointsDialog
from Gui.Dialogs import EditSurveysDialog
from Importers.Mnemo import MnemoImporter
from Models.ItemModels import SurveyCollection
from Utils.Storage import Save


class GlobalActions:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def exit_application(self):
        action = QAction('Exit', self.parent_window)
        action.setShortcut(KEY_QUIT_APPLICATION)
        action.triggered.connect(self.parent_window.close)
        return action

    def save(self):
        action = QAction('Save', self.parent_window)
        action.setShortcut(KEY_SAVE)
        action.triggered.connect(lambda: self.save_callback())
        return action

    def save_callback(self):
        pass

    def save_as(self):
        action = QAction('Save as', self.parent_window)
        action.setShortcut(KEY_SAVE_AS)
        action.triggered.connect(lambda: self.save_as_callback())
        return action

    def save_as_callback(self):
        file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
        file_ident = f'{APPLICATION_NAME} {file_regex}'
        dialog = QFileDialog()
        dialog.setWindowTitle('Save file')
        dialog.setFilter(dialog.filter())
        dialog.setDefaultSuffix(APPLICATION_FILE_EXTENSION)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters([file_ident])
        dialog.setDirectory(str(pathlib.Path.home()))
        dialog.setOption(QFileDialog.DontUseNativeDialog)
        if dialog.exec_() == QDialog.Accepted:
            file_name = dialog.selectedFiles()[0]
            if file_name[-4:] != f'.{APPLICATION_FILE_EXTENSION}':
                file_name = f'{file_name}.{APPLICATION_FILE_EXTENSION}'
            save = Save(file_name)
            save.save_to_file()

    def open(self):
        action = QAction('Open', self.parent_window)
        action.setShortcut(KEY_OPEN)
        action.triggered.connect(lambda: self.open_callback())
        return action

    def open_callback(self):
        try:
            file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
            file_ident = f'{APPLICATION_NAME} {file_regex}'
            name = QFileDialog.getOpenFileName(
                parent=self.parent_window,
                caption="Open file",
                dir=str(pathlib.Path.home()),
                filter=file_ident,
                selectedFilter=file_ident,
                options=QFileDialog.Options() | QFileDialog.DontUseNativeDialog
            )


            if not name[0]:
                return

            name = name[0]
            save = Save(name)
            data = save.open_from_file()
            ## Alright, I need to load the data into the application here.
            foo = 1
        except Exception as err_mesg:
            ErrorDialog.show_error_key(self.parent_window, str(err_mesg))

    def mnemo_connect_to(self):
        action = QAction('Connect to Mnemo', self.parent_window)
        action.setShortcut(KEY_IMPORT_MNEMO_CONNECT)
        action.triggered.connect(lambda: self.mnemo_connect_to_callback())
        return action

    def mnemo_connect_to_callback(self):
        self.parent_window.statusBar().showMessage('Connection to Mnemo...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        try:
            dmp = MnemoImporter()
            dmp.read_from_device()
            SurveyCollection.add_survey(dmp.get_data())
        except ConnectionError as err_mesg:
            ErrorDialog.show_error_key(self.parent_window, str(err_mesg))

    def mnemo_load_dump_file(self):
        action = QAction('Load Mnemo .dmp file', self.parent_window)
        action.setShortcut(KEY_IMPORT_MNEMO_DUMP_FILE)
        action.triggered.connect(lambda: self.mnemo_load_dump_file_callback())
        return action

    def mnemo_load_dump_file_callback(self):
        self.parent_window.statusBar().showMessage('Loading mnemo dump file...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        try:
            file = QFileDialog(self.parent_window)

            options = file.Options() | file.DontUseNativeDialog

            file.setOptions(options)
            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilters(['Mnemo dump file (*.dmp)', 'All files (*)'])
            file.setDirectory(str(pathlib.Path.home()))

            if file.exec() == QFileDialog.Accepted:
                file_name = file.selectedFiles()[0]
                dmp = MnemoImporter()
                dmp.read_dump_file(file_name)
                survey_id = dmp.get_data()
                # I need to get the treeview somehow.
                model = self.parent_window.tree_view.model()
                model.append_survey_from_db(survey_id)
                foo = 1

        except Exception as err_mesg:
            ErrorDialog.show_error_key(self.parent_window, str(err_mesg))

    def edit_survey(self):
        action = QAction('Edit surveys', self.parent_window)
        action.triggered.connect(lambda: self.edit_survey_callback())
        return action

    def edit_survey_callback(self):
        EditSurveysDialog.display(self.parent_window)


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
        msg.setInformativeText("Deleting this Section will delete all containing point too.")
        msg.setWindowTitle("Delete Section")
        #msg.setDetailedText("The details are as follows:")
        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        if msg.exec_() == QMessageBox.Ok:
            index = self.tree_view.selectedIndexes()[0]
            item = index.model().itemFromIndex(index)
            num_rows = item.model().delete_section(item)
            self.tree_view.parent().parent().statusBar().showMessage(f'Removed section, deleted {num_rows} rows from database.', MAIN_WINDOW_STATUSBAR_TIMEOUT)

        self.remove_alert.close()

    def edit_points(self):
        action = QAction('edit points', self.context_menu)
        action.triggered.connect(lambda: self.edit_points_callback())
        return action

    def edit_points_callback(self):
        index = self.tree_view.selectedIndexes()[0]
        item = index.model().itemFromIndex(index)
        dialog = EditPointsDialog(self.tree_view, item)
        dialog.show()

    def edit_point(self):
        pass

    def remove_point(self):
        pass
