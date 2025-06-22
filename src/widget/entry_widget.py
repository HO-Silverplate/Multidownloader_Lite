from PyQt6.QtWidgets import QLineEdit, QPushButton, QWidget, QHBoxLayout
from PyQt6.QtCore import pyqtSignal, Qt


class EntryWidget(QWidget):
    add_signal = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyleSheetTarget, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.hl = QHBoxLayout(self)
        self.hl.setContentsMargins(0, 0, 0, 0)
        self.lineedit = QLineEdit()
        self.lineedit.setPlaceholderText("Streamer ID")
        self.lineedit.setClearButtonEnabled(True)
        self.addButton = QPushButton("Add")
        self.addButton.clicked.connect(self.add)

        self.hl.addWidget(self.lineedit)
        self.hl.addWidget(self.addButton)

    def add(self):
        bjid = self.lineedit.text().strip()
        self.lineedit.clear()
        self.lineedit.setFocus()
        self.add_signal.emit(bjid)
