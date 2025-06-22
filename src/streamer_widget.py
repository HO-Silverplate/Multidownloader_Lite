from enum import Enum
import os
import time
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QFrame,
    QLineEdit,
    QComboBox,
    QSizePolicy,
)
from PyQt6.QtCore import QThread, QTimer, Qt
from PyQt6.QtGui import QPixmap
from streamlink import Streamlink
from streamlink.plugins.soop import SoopHLSStream, Soop
import requests
from src.util import resource_path

PLAYER_LIVE_API = "https://live.sooplive.co.kr/afreeca/player_live_api.php"

API_DATA_COMMON = {
    "from_api": "0",
    "mode": "landing",
    "player_type": "html5",
    "stream_type": "common",
}


OFFLINE = 0
ONLINE = 1
AUTH_FAIL = -6
ERROR = -100


class LiveStatus(Enum):
    BANGON = 0
    BANGJONG = 1
    LIVE = 2
    NOT_LIVE = 3
    LOGIN_REQUIRED = -1
    ERROR = -100


QUALITY_OPTIONS = ["best", "1440p", "1080p", "720p", "540p", "360p"]


class StreamerWidget(QWidget):
    def __init__(
        self,
        bjid,
        session: Streamlink,
        interval=10,
        auth_dict: dict[str, str] = {},
        output_dir="./Records",
    ):
        super().__init__()
        self.bjid = bjid
        self.output_dir = output_dir
        self.session = session
        self.prev_rescode = OFFLINE
        self.download_thread = None
        self.ui_init()

        self.option = {
            "afreeca-purge-credentials": True,
        }
        if auth_dict.get("username"):
            self.option["username"] = auth_dict["username"]
        if auth_dict.get("password"):
            self.option["password"] = auth_dict["password"]

        self.timer = QTimer()
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(self.check)
        self.timer.start()
        self.check()

    def ui_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyleSheetTarget, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("streamer_widget")

        self.setStyleSheet(
            """
            #streamer_widget {background-color: white; border-bottom: 1px solid #E0E0E0}
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.status_lamp = QLabel()
        self.status_lamp.setFixedSize(8, 8)
        self.status_lamp.setContentsMargins(0, 0, 0, 0)
        self.status_lamp.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self.bjid_label = QLabel(self.bjid)
        self.password_input = QLineEdit()
        self.password_input.setClearButtonEnabled(True)
        self.password_input.setPlaceholderText("방송 비밀번호")
        self.password_input.setFixedWidth(100)
        self.quality_spinbox = QComboBox()
        self.quality_spinbox.addItems(QUALITY_OPTIONS)
        self.quality_spinbox.setCurrentIndex(0)
        self.quality_spinbox.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Fixed
        )
        self.removeButton = QPushButton("[X]")
        self.removeButton.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self.removeButton.setFixedWidth(30)
        self.removeButton.setFixedHeight(24)
        self.removeButton.clicked.connect(self._stop_download)

        self.hl = QHBoxLayout(self)
        self.hl.addWidget(self.status_lamp)
        self.hl.addWidget(self.bjid_label)
        self.hl.addStretch(1)
        self.hl.addWidget(self.password_input)
        self.hl.addWidget(self.quality_spinbox)
        self.hl.addWidget(self.removeButton)

    def check(self):
        response = requests.post(
            PLAYER_LIVE_API,
            data={
                **API_DATA_COMMON,
                "bid": self.bjid,
                "type": "live",
            },
        )
        response.raise_for_status()

        chn: dict = response.json().get("CHANNEL", {})
        bjnick = chn.get("BJNICK", "")
        title = chn.get("TITLE", "")
        rescode = chn.get("RESULT", ERROR)

        if rescode == AUTH_FAIL or rescode == ERROR:  # 로그인 필요
            status = LiveStatus.LOGIN_REQUIRED

        if self.prev_rescode == OFFLINE and rescode != OFFLINE:  # 뱅온
            status = LiveStatus.BANGON
        elif self.prev_rescode != OFFLINE and rescode == OFFLINE:  # 뱅종
            status = LiveStatus.BANGJONG
        elif self.prev_rescode != OFFLINE and rescode != OFFLINE:  # 방송 지속
            status = LiveStatus.LIVE
        else:  # 방송 없음 지속
            status = LiveStatus.NOT_LIVE

        self._update_lamp(status)
        if status == LiveStatus.BANGON and not self.download_thread:
            self._start_download(
                output_path=os.path.join(
                    self.output_dir,
                    f"[{bjnick}({self.bjid})][{time.strftime('%Y%m%d')}]{title}.ts",
                )
            )
        elif status == LiveStatus.BANGJONG:
            self._stop_download()

    def _update_lamp(self, status: LiveStatus):
        if status == LiveStatus.BANGON or status == LiveStatus.LIVE:
            pixmap = QPixmap(resource_path("resources/green.png")).scaledToWidth(8)
        elif status == LiveStatus.BANGJONG or status == LiveStatus.NOT_LIVE:
            pixmap = QPixmap(resource_path("resources/red.png")).scaledToWidth(8)
        elif status == LiveStatus.LOGIN_REQUIRED:
            pixmap = QPixmap(resource_path("resources/yellow.png")).scaledToWidth(8)
        else:
            pixmap = QPixmap(resource_path("resources/black.png")).scaledToWidth(8)

        self.status_lamp.setPixmap(pixmap)
        self.status_lamp.update()

    def _start_download(self, output_path):
        print("Starting download...")
        quality = self.quality_spinbox.currentText()
        if self.password_input.text() and self.password_input.text().strip() != "":
            self.option["stream-password"] = self.password_input.text().strip()

        soop = Soop(
            session=self.session,
            url=f"https://play.sooplive.co.kr/{self.bjid}",
            options=self.option,
        )
        streams: dict[str, SoopHLSStream] = soop.streams()
        if not streams:
            return

        target_stream: SoopHLSStream | None = streams.get(quality, None)
        if not target_stream:
            print("no target")
            return

        self.download_thread = download_thread(
            stream=target_stream, output_path=output_path
        )
        self.download_thread.start()

    def _stop_download(self):
        if hasattr(self, "download_thread") and self.download_thread.isRunning():
            self.download_thread.cleanup()
            self.download_thread.wait()
            del self.download_thread


class download_thread(QThread):
    power = True

    def __init__(self, stream: SoopHLSStream, output_path="output.ts"):
        super().__init__()
        self.stream = stream
        self.output_path = output_path

    def run(self):
        self.power = True
        streamreader = self.stream.open()
        if not os.path.exists(os.path.dirname(self.output_path)):
            os.makedirs(os.path.dirname(self.output_path))
        with open(self.output_path, "wb") as f:
            while self.power:
                bytes = streamreader.read(8192)  # Read 8KB at a time
                if not bytes:
                    break
                f.write(bytes)

    def cleanup(self):
        print("Stopping download...")
        time.sleep(0.5)
        self.power = False
