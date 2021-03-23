import PySide6
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QItemDelegate, QComboBox

#  http://programmingexamples.net/wiki/Qt/Delegates/ComboBoxDelegate
class DropDown(QItemDelegate):

    def __init__(self, parent):
        super().__init__(parent)
        self._options = ["setOptions() not called"]

    def setOptions(self, options=['YES', 'NO']):
        self._options = options

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        for item in self._options:
            combo.addItem(item)
        return combo

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)
