from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QProgressDialog

from Gui.Dialogs import ErrorDialog
from Models.TableModels import SqlManager


class WorkerMixin(QObject):
    s_finished = Signal()
    s_error = Signal(str, Exception)
    s_progress = Signal(int)
    s_task_label = Signal(str)
    s_reload_treeview = Signal(int)

    def __init__(self):
        super().__init__()
        self._sql_manager = None

    def set_sql_manager(self, connection_name: str = None):
        self._sql_manager = SqlManager(connection_name)
        return self._sql_manager

    def sql_manager(self):
        return self._sql_manager

    def finished(self):
        if self._sql_manager is not None:
            self._sql_manager.close_connection()
        self.s_finished.emit()

    def run(self, thread_action: str):
        raise NotImplementedError('run() is a required method, please implement it.')

class ThreadWithProgressBar:
    """
        Use-case:
        I need to import a big file (Mnemo).
        While doing this I want to show a progressbar that updates both the label as the progressbar itself.

        Subclass this object, and prepare the thread (see the GlobalActions object)
        The threaded object should subclass the above mixin as it has all the required slots.

        Your threaded object HAS TO USE the "set_sql_manager()", "sql_manager()" and "finished()" methods in order to use a database.

        @todo multiple threads within the same parent object is not possible right now.
    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None
        self.progress = None
        self.running_thread = None

        self.on_finish = None

    def worker_is_running(self, thread_name: str) -> bool:
        if self.running_thread == thread_name:
            return True
        return False

    def worker_create_thread(self,
                             thread_object: QObject,
                             on_finish: None,
                             progress_params: dict = {
                                 "title": "default title",
                                 "value": 0,
                                 "min": 0,
                                 "max": 0
                             }):
        if self.running_thread is not None:
            ErrorDialog.show(f'{self.running_thread} is already running, we don\'t support multiple threads here')
            return

        self.on_finish = on_finish

        self.worker_create_progress_dialog(**progress_params)

        self.thread = QThread()
        self.worker = thread_object
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.s_finished.connect(self.thread.quit)
        self.worker.s_finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.s_finished.connect(self.worker_finished)
        self.worker.s_progress.connect(self.worker_update_progress)
        self.worker.s_task_label.connect(self.worker_update_task_label)
        self.worker.s_error.connect(self.worker_error)
        self.worker.s_reload_treeview.connect(self.worker_treeview_reload)

    def worker_start(self, thread_name: str = 'default'):
        self.running_thread = thread_name
        self.thread.start()

    def worker_create_progress_dialog(self, title: str, value: int = 0, min_value: int = 0, max_value: int = 0):
        # wrap this in a thread, this is blocking...
        self.progress = QProgressDialog(self.main_window)
        self.progress.setWindowTitle(title)
        self.progress.setValue(value)
        self.progress.showNormal()
        self.progress.setMinimum(min_value)
        self.progress.setMaximum(max_value)
        self.progress.show()

        self.progress.canceled.connect(self.worker_progress_cancelled)

    def worker_update_progress(self, value: int):
        self.progress.setValue(value)

    def worker_update_task_label(self, label: str):
        self.progress.setLabelText(label)

    def worker_finished(self):
        self.progress.close()
        self.thread.quit()
        if self.on_finish is not None:
            self.on_finish()

        self.running_thread = None

    def worker_error(self, error_key: str, error_exception: Exception = None):
        ErrorDialog.show_error_key(self.main_window, error_key, error_exception)

    def worker_progress_cancelled(self):
        self.thread.quit()
        self.running_thread = None

    def worker_treeview_reload(self, survey_id):
        # I need to get the treeview somehow.
        model = self.main_window.tree_view.model()
        model.append_survey_from_db(survey_id)

