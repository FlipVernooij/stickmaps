import sys

from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QApplication, QMainWindow, QTreeView, QDialog


class MyTreeView(QTreeView):
    def __init__(self, parent):
        super().__init__(parent)
        model = MyModel()
        self.setModel(model)


class MyModel(QStandardItemModel):
    def __init__(self):
        super().__init__()
        self.root_item = self.invisibleRootItem()
        self.top_level = QStandardItem("Top level")
        self.root_item.appendRow(self.top_level)

        self.top_level.appendRow(QStandardItem('Appended item'))
        t = QStandardItem('Inserted item')
        self.top_level.insertRow(0, t)

class MainApplicationWindow(QMainWindow):
    def __init__(self):
        super(MainApplicationWindow, self).__init__()
        self.setWindowTitle('TEST QAction')
        self.tree = MyTreeView(self)
        self.setCentralWidget(self.tree)
        self.show()

if __name__ == '__main__':

    if __name__ == '__main__':
        parent_app = QApplication(sys.argv)

        app = MainApplicationWindow()

        sys.exit(parent_app.exec_())
