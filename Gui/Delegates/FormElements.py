from datetime import datetime

from PySide6.QtCore import Qt, QDateTime, QModelIndex
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QItemDelegate, QComboBox, QPlainTextEdit, QDateTimeEdit, QStyleOptionViewItem, \
    QStyle


#  http://programmingexamples.net/wiki/Qt/Delegates/ComboBoxDelegate
class DropDown(QItemDelegate):

    def __init__(self, parent):
        super().__init__(parent)
        self._options = ["setOptions() not called"]

    def setOptions(self, options=['YES', 'NO']):
        self._options = options

    def createEditor(self, parent, style_options, index):
        combo = QComboBox(parent)
        for item in self._options:
            combo.addItem(item)
        return combo

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)


class DateTimeEditor(QItemDelegate):

    def __init__(self, parent):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        # @todo for some reason when I select the column, it doesn't get selected.
        #       yet this code supposed to be correct and problem might be related to events?
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        value = index.model().data(index, Qt.EditRole)
        value = datetime.fromtimestamp(value).ctime()
        painter.drawText(option.rect, Qt.AlignVCenter, value)

    def createEditor(self, parent, style_options, index):
        editor = QDateTimeEdit(parent)
        return editor

    def setEditorData(self, editor: QDateTimeEdit, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setDateTime(QDateTime(datetime.fromtimestamp(value)))

    def setModelData(self, editor: QDateTimeEdit, model, index):
        value = editor.dateTime().toSecsSinceEpoch()
        model.setData(index, 'userRole', Qt.UserRole)
        model.setData(index, 'displayRole', Qt.DisplayRole)
        model.setData(index, value, Qt.EditRole)


class CommentEditor(QItemDelegate):

    def __init__(self, parent):
        super().__init__(parent)

    def createEditor(self, parent, style_options, index):
        editor = QPlainTextEdit(parent)
        # @todo When we show this for the last row in the table, the field is "scrolled out of view"
        #       .. We should probably make it a dialog or something...
        editor.setMinimumHeight(200)
        return editor

    def setEditorData(self, editor: QPlainTextEdit, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setPlainText(value)

    def setModelData(self, editor: QPlainTextEdit, model, index):
        model.setData(index, editor.toPlainText(), Qt.EditRole)