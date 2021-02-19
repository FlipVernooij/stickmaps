import pathlib

from PySide6.QtGui import QAction

from PySide6.QtWidgets import QFileDialog, QTreeView, QMenu

from Config.Constants import MAIN_WINDOW_STATUSBAR_TIMEOUT, SQL_TABLE_SURVEYS
from Gui.Dialogs import ErrorDialog, EditSurveyDialog
from Gui.Dialogs import EditSurveysDialog
from Importers.Mnemo import MnemoImporter
from Models.TableModels import Survey
from Models.TreeViews import SurveyCollection


class GlobalActions:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def exit_application(self):
        action = QAction('Exit', self.parent_window)
        action.setShortcut('Ctrl+Q')
        action.triggered.connect(self.parent_window.close)
        return action

    def mnemo_connect_to(self):
        action = QAction('Connect to Mnemo', self.parent_window)
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
        action.triggered.connect(lambda: self.mnemo_load_dump_file_callback())
        return action

    def mnemo_load_dump_file_callback(self):
        self.parent_window.statusBar().showMessage('Loading mnemo dump file...', MAIN_WINDOW_STATUSBAR_TIMEOUT)
        try:
            file = QFileDialog(self.parent_window)

            options = file.Options()
            options |= file.DontUseNativeDialog

            file.setOptions(options)
            file.setWindowTitle('Select Mnemo .dmp file to load')
            file.setNameFilters(['Mnemo dump file (*.dmp)', 'All files (*)'])
            file.setDirectory(str(pathlib.Path.home()))

            if file.exec() == QFileDialog.Accepted:
                file_name = file.selectedFiles()[0]
                dmp = MnemoImporter()
                dmp.read_dump_file(file_name)
                dmp.get_data()
                print("refresh_treeView() was called.")
                # SurveyCollection.dataChanged.emit(SurveyCollection.index())

                """
                    I need to send a signal here.. yet I do not understand the params (yet)
                        'PySide6.QtCore.Signal' object has no attribute 'emit'
                    GL!
                """

                SurveyCollection.update_view()
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

    def edit(self):
        action = QAction('edit', self.context_menu)
        action.triggered.connect(lambda: self.edit_callback(self.tree_view))
        return action

    def edit_callback(self, *args, **kwargs):
        index = self.tree_view.selectedIndexes()[0]
        item = index.model().itemFromIndex(index)
        try:
            point_id = item.point_id
            return
        except AttributeError:
            pass

        try:
            section_id = item.section_id
        except AttributeError:
            pass

        try:
            survey = Survey.get(SQL_TABLE_SURVEYS, 'survey_id=?', [item.survey_id])
            form = EditSurveyDialog(self.tree_view, survey)
            form.show()
        except AttributeError:
            pass