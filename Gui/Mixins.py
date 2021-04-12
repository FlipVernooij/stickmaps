import pathlib

from PySide6.QtCore import QSettings
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QLabel, QPushButton, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit, \
    QFormLayout, QHBoxLayout, QFileDialog, QDialog, QRadioButton, QTextEdit

from Config.Constants import APPLICATION_DEFAULT_FILE_NAME, APPLICATION_FILE_EXTENSION, APPLICATION_NAME
from Utils.Settings import Preferences


class FormMixin:

    def field_changed(self, arg=None):
        self.form_changed = True

    def generate_form(self, form_fields: dict, form_layout: QFormLayout, _is_group_field=False):
        if _is_group_field is False:
            while form_layout.rowCount() > 0:
                form_layout.removeRow(form_layout.rowCount() - 1)

        for key in form_fields['fields'].keys():
            element = form_fields['fields'][key]
            if element['form_field'] == 'group_field':
                el = QHBoxLayout()
                self.generate_form(element, el, True)
                form_layout.addRow(element['label'], el)
                continue
            if element['form_field'] == 'spacer':
                form_layout.addRow("  ", None)  # Don't remove spaces ;p
                continue

            if 'default_value' in element and 'settings_key' in element:
                element['default_value'] = Preferences.get(element['settings_key'], element['default_value'])
            form_fields['fields'][key]['form_element'] = self.get_field(element)

            if _is_group_field is True:
                form_fields['fields'][key]['form_element'].setMinimumWidth(0)
                form_layout.addWidget(form_fields['fields'][key]['form_element'])
                continue

            label = QLabel(element['label'])
            label.setMinimumWidth(150)
            if 'info' in element:
                label.setToolTip(f"{element['info']}")

            form_layout.addRow(label, form_fields['fields'][key]['form_element'])

    def get_field(self, element: dict):
        f = element['form_field']
        if f == 'text_line':
            el = QLineEdit(self)
            if 'default_value' in element:
                el.setText(str(element['default_value']))
            if 'placeholder' in element:
                el.setPlaceholderText(str(element['placeholder']))
            el.setClearButtonEnabled(True)
            el.textChanged.connect(self.field_changed)
        elif f == 'check_box':
            el = QCheckBox(self)
            el.setChecked(bool(int(element['default_value'])))
            el.stateChanged.connect(self.field_changed)
        elif f == 'combo_box':
            el = QComboBox(self)
            el.addItems(element['options'])
            el.setCurrentText(str(element['default_value']))
            el.currentTextChanged.connect(self.field_changed)
        elif f == 'spinner':
            if 'is_float' in element.keys() and element['is_float'] is True:
                el = QDoubleSpinBox()
                try:
                    el.setDecimals(element['decimals'])
                except KeyError:
                    el.setDecimals(2)
            else:
                el = QSpinBox(self)
            try:
                el.setMinimum(element['min'])
            except KeyError:
                pass
            try:
                el.setMaximum(element['max'])
            except KeyError:
                pass

            if 'default_value' in element:
                el.setValue(int(element['default_value']))
            el.valueChanged.connect(self.field_changed)
        elif f == 'button':
            el = QPushButton(element['button_label'])
            el.clicked.connect(getattr(self, element['action']))
        elif f == 'label':
            if "value_from_function" in element:
                element['value'] = getattr(self, element["value_from_function"])(element)
            el = QLabel(element['value'])
        elif f == 'textarea':
            if "value_from_function" in element:
                element['value'] = getattr(self, element["value_from_function"])(element)
            el = QTextEdit(element['value'])
            el.setDisabled(True)
        elif f == 'save_file_path':
            el = QHBoxLayout()
            file_path = QLineEdit(self)
            file_path.setClearButtonEnabled(True)
            settings = QSettings()
            file_name = f'{settings.value("SaveFile/last_path", str(pathlib.Path.home()))}/{APPLICATION_DEFAULT_FILE_NAME}'
            file_path.setText(file_name)
            el.addWidget(file_path)
            style = self.style()
            button = QPushButton(QIcon(style.standardIcon(style.SP_DirHomeIcon)), 'Choose file')
            el.addWidget(button)
            button.clicked.connect(lambda: self._show_save_path_dialog(file_path))
        elif f == 'radio_button':
            el = QRadioButton()
        elif f == 'group_field':
            # lets ignore this one and parse it at the generate form...
            # this way we can easily add the objects to the form array.
            return None
        elif f == 'spacer':
            # lets ignore this one and parse it at the generate form...
            return None
        else:
            el = QLabel(f"Unknown form_field {f}")
            # raise AttributeError(f'Unknown form_field in preferences plain: "{f}"')

        if 'disabled' in element and element['disabled'] is True:
            el.setDisabled(True)

        if 'dev_only' in element and element['dev_only'] is True:
            if Preferences.debug() is False:
                el.setDisabled(True)

        if 'field_changed' in element:
            el.stateChanged.connect(getattr(self, element['field_changed']))

        try:
            el.setMinimumWidth(200)
        except AttributeError:
            pass
        return el

    def get_field_value(self, element: dict):
        f = element['form_field']
        e = element['form_element']
        if f == 'text_line':
            return e.text()
        elif f == 'check_box':
            return int(e.isChecked())
        elif f == 'combo_box':
            return e.currentText()
        elif f == 'spinner':
            return e.value()
        elif f in ('save_file_path', 'open_file_path',):
            return e.itemAt(0).widget().text()
        else:
            raise AttributeError(f'Unknown form_field in preferences plain: "{f}"')

    def _show_save_path_dialog(self, form_field: QLineEdit):
        settings = QSettings()
        file_regex = f'(*.{APPLICATION_FILE_EXTENSION})'
        file_ident = f'{APPLICATION_NAME} {file_regex}'
        dialog = QFileDialog()
        dialog.setWindowTitle('Create file')
        dialog.setFilter(dialog.filter())
        dialog.setDefaultSuffix(APPLICATION_FILE_EXTENSION)
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilters([file_ident])
        dialog.setDirectory(settings.value('SaveFile/last_path', str(pathlib.Path.home())))
        dialog.setOption(QFileDialog.DontUseNativeDialog)
        if dialog.exec_() == QDialog.Accepted:
            file_name = dialog.selectedFiles()[0]
            if file_name[-4:] != f'.{APPLICATION_FILE_EXTENSION}':
                file_name = f'{file_name}.{APPLICATION_FILE_EXTENSION}'
            form_field.setText(file_name)
            dialog.close()
