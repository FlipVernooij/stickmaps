from PySide6.QtWidgets import QErrorMessage


class ErrorDialog(QErrorMessage):

    errorMessages = {
        'UNKNOWN_ERROR': {
            'title': "Unknown error occurred",
            'body': "Bang head against screen and try again."
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

    def __init__(self, parent):
        self.parent = parent
        super(ErrorDialog, self).__init__(parent=parent)

    def show(self, error_key):
        try:
            title = self.errorMessages[error_key]['title']
            body = self.errorMessages[error_key]['body']
        except:
            title = self.errorMessages['UNKNOWN_ERROR']['title']
            body = self.errorMessages['UNKNOWN_ERROR']['body']

        self.resize(500, 250)
        self.setWindowTitle(title)
        self.showMessage(body)
        if self.errorMessages[error_key]['status']:
            self.parent.statusBar().showMessage(self.errorMessages[error_key]['status'], self.parent.STATUSBAR_TIMEOUT)

        super(ErrorDialog, self).show()