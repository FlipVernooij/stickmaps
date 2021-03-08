from Gui.Actions import GlobalActions


class MainMenu:

    def __init__(self, parent_window):
        self.parent_window = parent_window

    def generate(self):
        self.set_file_menu()
        self.set_edit_menu()
        self.set_import_menu()

    def set_file_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('File')

        fm.addAction(actions.new())
        fm.addAction(actions.open())
        fm.addAction(actions.save())
        fm.addAction(actions.save_as())
        fm.addAction(actions.exit_application())

    def set_edit_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Edit')
        fm.addAction(actions.edit_survey())

    def set_import_menu(self):
        actions = GlobalActions(self.parent_window)
        mb = self.parent_window.menuBar()
        fm = mb.addMenu('Import')
        fm.addAction(actions.mnemo_connect_to())
        fm.addAction(actions.mnemo_load_dump_file())
        fm.addAction(actions.mnemo_dump())

