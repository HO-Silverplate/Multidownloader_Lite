import json
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextOption
from streamlink import Streamlink

from .util import LogWriter
from .widget import EntryWidget, StreamerWidget

CONFIG_FILE = "config.json"


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multidownloader Lite")
        self.setMinimumHeight(504)
        self.setMinimumWidth(400)

        self.streamlinkSession = Streamlink()
        self.bj_list = []

        self.config = self.read_options()
        self.logwriter = LogWriter()
        self.ui_init()

        self.logwriter.info("Application started.")
        self.logwriter.info(
            f"Path Set to : {self.config.get('rec_location', './Records')}"
        )
        self.logwriter.info(
            f"Interval Set to : {self.config.get('refresh_sec', 10)} seconds"
        )

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
        self.logwriter.msg_sig.connect(self.log_window.append)

        self.vl.addWidget(self.scroll_area)
        self.vl.addWidget(self.log_window)
        self.vl.addWidget(self.entry_widget)

    def add_new_streamer(self, bjid: str):
        if not bjid or bjid in self.bj_list:
            return
        try:
            self.bj_list.append(bjid)
            widget = StreamerWidget(
                bjid, self.streamlinkSession, self.logwriter, self.config
            )
            self.scroll_layout.addWidget(widget)
            widget.removeButton.clicked.connect(lambda: self.remove_streamer(widget))
        except Exception as e:
            self.logwriter.error(f"Error adding new streamer widget: {e}")
            return

    def remove_streamer(self, widget: StreamerWidget):
        try:
            self.bj_list.remove(widget.bjid)
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
            widget.timer.stop()
        except Exception as e:
            self.logwriter.error(f"Error removing streamer widget: {e}")

    def read_options(self) -> dict:
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    return config
            else:
                return {}
        except Exception as e:
            self.logwriter.error(f"Error reading config file: {e}")
            return {}
