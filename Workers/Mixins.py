from PySide6.QtCore import QObject, QThread
from PySide6.QtWidgets import QProgressDialog

from Gui.Dialogs import ErrorDialog


class WorkerProgress:
    """
        This worker is used to thread stuff mainly within the menu-actions.
        It will dispatch a thread and show a progressbar untill finished.

        In order to use this, your thread_object needs the following signals:

        # emit this to update the progress.
        progress = Signal(int)
        # emit this to update the text within the progressbar dialog
        task_label = Signal(str)
        # emit this when task is finished
        finished = Signal()
        # emit this on error (don't forget to emit finished to!)
        error = Signal(str, exception)

    """
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.thread = None
        self.worker = None
        self.progress = None
        self.running_thread = None

    def worker_is_running(self, thread_name: str) -> bool:
        if self.running_thread == thread_name:
            return True
        return False

    def worker_create_thread(self,
                             thread_object: QObject,
                             progressparams: dict = {
                                 "title": "default title",
                                 "value": 0,
                                 "min": 0,
                                 "max": 0
                             }):
        if self.running_thread is not None:
            ErrorDialog.show(f'{self.running_thread} is already running, we don\'t support multiple threads here')
            return

        self.worker_create_progress_dailog(**progressparams)

        self.thread = QThread()
        self.worker = thread_object
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.finished.connect(self.worker_finished)
        self.worker.progress.connect(self.worker_update_progress)
        self.worker.task_label.connect(self.worker_update_task_label)
        self.worker.error.connect(self.worker_error)

    def worker_start(self, thread_name: str = 'default'):
        self.running_thread = thread_name
        self.thread.start()

    def worker_create_progress_dailog(self, title: str, value: int = 0, min_value: int = 0, max_value: int = 0):
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
        self.running_thread = None

    def worker_error(self, error_key: str, error_exception: Exception = None):
        ErrorDialog.show_error_key(self.main_window, error_key, error_exception)

    def worker_progress_cancelled(self):
        self.thread.quit()
        self.running_thread = None
