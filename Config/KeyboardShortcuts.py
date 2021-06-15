from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

KEY_QUIT_APPLICATION = QKeySequence("Ctrl+Q")
KEY_SAVE = QKeySequence("Ctrl+S")
KEY_SAVE_AS = QKeySequence("Ctrl+Shift+S")
KEY_OPEN = QKeySequence("Ctrl+O")
KEY_NEW = QKeySequence("Ctrl+N")
KEY_PREFERENCES = QKeySequence("Ctrl+,")

KEY_IMPORT_MNEMO_CONNECT = QKeySequence("Ctrl+Shift+M")
KEY_IMPORT_MNEMO_DUMP_FILE = QKeySequence("Ctrl+Alt+M")
KEY_IMPORT_MNEMO_DUMP = QKeySequence("Ctrl+Meta+M")

KEY_TOGGLE_SATELLITE = QKeySequence("Ctrl+M")
KEY_ZOOM_IN = QKeySequence('Ctrl+-')  # QKeySequence.ZoomIn <= doesn't seem to work either ;(
KEY_ZOOM_OUT = QKeySequence('Ctrl+=')  # QKeySequence.ZoomIn <= doesn't allow the = so it becomes Ctrl+Shift++
