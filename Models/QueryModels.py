from PySide6.QtCore import Qt
from PySide6.QtSql import QSqlQueryModel, QSqlQuery


class EditableQueryModel(QSqlQueryModel):

    def __init__(self, parent, editables: list = []):
        super().__init__(parent)
        self.editables = editables

    def flags(self, index):
        fl = QSqlQueryModel.flags(self, index)
        if index.column() == 1:
            fl |= Qt.ItemIsEditable
        return fl

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            mycolumn = index.column()
            if mycolumn in self.editables:
                (query, filter_col) = self.editables[mycolumn]
                filter_value = self.index(index.row(), filter_col).data()
                q = QSqlQuery(query.format(value, filter_value))
                result = q.exec_()
                if result:
                    self.query().exec_()
                else:
                    print(self.query().lastError().text())
                return result
        return QSqlQueryModel.setData(self, index, value, role)