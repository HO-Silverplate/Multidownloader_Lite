from .entry_widget import EntryWidget
from .streamer_widget import StreamerWidget
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextOption
from streamlink import Streamlink


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PyQt6 Example")
        self.setMinimumHeight(500)
        self.setMinimumWidth(400)

        self.streamlinkSession = Streamlink()
        self.ui_init()
        self.bj_list = []

    def ui_init(self):
        self.vl = QVBoxLayout(self)
        self.setLayout(self.vl)
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)
        self.scroll_area.setWidget(self.scroll_widget)

        self.entry_widget = EntryWidget()
        self.entry_widget.add_signal.connect(self.add_new_streamer)

        self.log_window = QTextEdit()
        self.log_window.setFixedHeight(150)
        self.log_window.setReadOnly(True)
        self.log_window.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.log_window.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)

        self.vl.addWidget(self.scroll_area)
        self.vl.addWidget(self.log_window)
        self.vl.addWidget(self.entry_widget)

    def add_new_streamer(self, bjid: str):
        if not bjid or bjid in self.bj_list:
            return

        self.bj_list.append(bjid)
        widget = StreamerWidget(
            bjid,
            self.streamlinkSession,
        )
        self.scroll_layout.addWidget(widget)
        widget.removeButton.clicked.connect(lambda: self.remove_streamer(widget))
        print(widget)

    def remove_streamer(self, widget: StreamerWidget):
        self.bj_list.remove(widget.bjid)
        self.scroll_layout.removeWidget(widget)
        widget.deleteLater()
