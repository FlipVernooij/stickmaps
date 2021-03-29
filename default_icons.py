import sys

from PySide6.QtWidgets import QWidget, QGridLayout, QPushButton, QStyle, QApplication


class Widget(QWidget):

    def __init__(self, parent=None):
        super(Widget, self).__init__()

        colSize = 4

        layout = QGridLayout()

        style = self.style()
        properties = dir(style)

        count = 0
        for i in properties:
            if i.startswith('SP_'):

                btn = QPushButton(i)
                btn.setIcon(self.style().standardIcon(getattr(QStyle, i)))

                layout.addWidget(btn, count / colSize, count % colSize)
                count += 1

        self.setLayout(layout)


if __name__ == '__main__':
    app = QApplication(sys.argv)

    dialog = Widget()
    dialog.show()

    app.exec_()