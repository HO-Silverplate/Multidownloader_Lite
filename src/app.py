import json
import os
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QTextOption
import requests
from streamlink import Streamlink

from .util import LogWriter
from .widget import EntryWidget, StreamerWidget

CONFIG_FILE = "config.json"
LOGIN_URL = "https://login.sooplive.co.kr/app/LoginAction.php"


class App(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multidownloader Lite")
        self.setMinimumHeight(504)
        self.setMinimumWidth(400)

        self.streamlinkSession = Streamlink()
        self.bj_dict: dict[str, StreamerWidget] = {}

        self.logwriter = LogWriter()
        self.ui_init()

        self.logwriter.info("Application started.")
        self.config = self.read_options()
        self.logwriter.info(
            f"Path Set to : {self.config.get('rec_location', './Records')}"
        )
        self.logwriter.info(
            f"Interval Set to : {self.config.get('refresh_sec', 10)} seconds"
        )
        self.requestSession = requests.Session()
        self.requestSession = self.login_to_soop(
            self.config.get("user_name", ""),
            self.config.get("user_password", ""),
            self.requestSession,
        )
        if strms := self.config.get("streamers"):
            for bjid in strms:
                self.add_new_streamer(bjid)

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
        if not bjid or bjid in self.bj_dict.keys():
            return
        try:
            widget = StreamerWidget(
                bjid,
                self.streamlinkSession,
                self.requestSession,
                self.logwriter,
                self.config,
            )
            self.bj_dict[bjid] = widget
            self.scroll_layout.addWidget(widget)
            widget.removeButton.clicked.connect(lambda: self.remove_streamer(bjid))

        except Exception as e:
            self.logwriter.error(f"Error adding new streamer widget: {e}")
            return

    def remove_streamer(self, bjid: str):
        try:
            widget = self.bj_dict.pop(bjid)
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
            widget.timer.stop()
        except Exception as e:
            self.logwriter.error(f"Error removing streamer widget: {e}")

    def read_options(self) -> dict:
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "rb") as f:
                    config = json.loads(f.read().decode("utf-8"))
                    return config
            else:
                return {}
        except Exception as e:
            self.logwriter.error(f"Error reading config file: {e}")
            return {}

    def closeEvent(self, event):
        for _ in range(self.bj_dict.__len__()):
            self.remove_streamer(list(self.bj_dict.keys())[0])
        super().closeEvent(event)

    def login_to_soop(
        self, username: str, password: str, session: requests.Session
    ) -> requests.Session:
        try:
            response = session.post(
                LOGIN_URL,
                data={
                    "szWork": "login",
                    "szType": "json",
                    "szUid": username,
                    "szPassword": password,
                    "szScriptVar": "oLoginRet",
                    "isSaveId": "false",
                    "isSavePw": "false",
                    "isSaveJoin": "false",
                    "isLoginRetain": "false",
                },
            )
            response.raise_for_status()
            if (rescode := response.json().get("RESULT", 1024)) != 1:
                self.logwriter.error(f"Login failed - CODE: {rescode}")
            else:
                self.logwriter.info("Login successful")
        except:
            self.logwriter.error(f"Login failed for {username}: {response.status_code}")
        finally:
            return session
