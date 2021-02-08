from PySide6.QtSql import QSqlDatabase, QSqlQuery

from Config.Constants import APPLICATION_NAME

from PySide6.QtWidgets import QMessageBox


class Sqlite:

    _connection_ = None

    @classmethod
    def get_connection(cls, connection_name='qt_sql_default_connection'):
        if cls._connection_ is None:
            db = QSqlDatabase.addDatabase('QSQLITE', connectionName=connection_name)
            db.setDatabaseName(':memory:')
            if not db.open():
                QMessageBox.warning(None, APPLICATION_NAME, "Database Error: {}".format(db.lastError().text()))
            cls._connection_ = db
        return cls._connection_

    @classmethod
    def exec(cls, sql):
        query = QSqlQuery(db=cls.get_connection())
        return query.exec_(sql)

    @classmethod
    def insert(cls, table_name: str, values: dict):
        col_names = ', '.join(values.keys())
        placeholders = ', '.join('?' for x in values.values())
        query = 'INSERT INTO {} ({})VALUES({})'.format(table_name, col_names, placeholders)
        obj = QSqlQuery(db=cls.get_connection())
        obj.prepare(query)

        params_bound = []
        for value in values.values():
            params_bound.append(value)
            obj.addBindValue('kaas')

        if obj.exec_() is False:
            raise SyntaxError('Sql insert query failed!')
        insert_id = obj.lastInsertId()
        obj.clear()
        return insert_id

    @classmethod
    def update(cls, table_name, values, where_str, params):
        update_cols = ', '.join('{}=?'.format(x) for x in values.keys())
        query = 'UPDATE {} SET {} WHERE {}'.format(table_name, update_cols, where_str)
        obj = QSqlQuery(db=cls.get_connection())
        obj.prepare(query)

        for value in values.values():
            obj.addBindValue(value)
        for value in params.values():
            obj.addBindValue(value)

        obj.exec_()
        return obj.numRowsAffected()

    @classmethod
    def get(cls, table_name, where_str, params):
        if type(params) is not list:
            params = [params]

        query = f"SELECT * FROM {table_name} WHERE {where_str}"
        obj = QSqlQuery(db=cls.get_connection())
        obj.prepare(query)

        for param in params:
            obj.addBindValue(param)

        obj.exec_()
        if obj.size() != 1:
            raise ValueError('Sqlite::get() can only return one row')

        obj.first()
        row = {}
        for index in range(0, obj.record().count()):
            row[obj.record().fieldName(index)] = obj.value(index)

        return row

    @classmethod
    def fetch(cls, sql, params):
        if type(params) is not list:
            params = [params]

        obj = QSqlQuery(db=cls.get_connection())
        obj.prepare(sql)

        for param in params:
            obj.addBindValue(param)

        obj.exec_()
        obj.first()
        row = {}
        for index in range(0, obj.record().count()):
            row[obj.record().fieldName(index)] = obj.value(index)
            yield row

