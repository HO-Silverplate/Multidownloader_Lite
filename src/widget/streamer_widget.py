from enum import Enum
import os
import re
import time
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QLineEdit,
    QComboBox,
    QSizePolicy,
)
from PyQt6.QtCore import QThread, QTimer, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from streamlink import Streamlink
from streamlink.plugins.soop import SoopHLSStream, Soop
import requests
from src.util import LogWriter, resource_path, get_unique_filename, parse_byte_size

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
        requestSession: requests.Session,
        logwriter: LogWriter,
        config: dict[str, str] = {},
    ):
        super().__init__()
        self.bjid = bjid
        self.session = session
        self.prev_rescode = OFFLINE
        self.download_thread = None
        self.logwriter = logwriter

        self.option = {
            "afreeca-purge-credentials": True,
        }
        if username := config.get("user_name"):
            self.option["username"] = username
        if password := config.get("user_password"):
            self.option["password"] = password
        self.output_dir = config.get("rec_location", "./Records")

        interval = int(config.get("refresh_sec", 10))
        self.timer = QTimer()
        self.timer.setInterval(interval * 1000)
        self.timer.timeout.connect(lambda: self.check(requestSession))
        self.timer.start()

        self.progress_timer = QTimer()
        self.progress_timer.setInterval(1000)
        self.progress_timer.timeout.connect(self.update_progress)
        self.ui_init()
        self.check(requestSession)

    def ui_init(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyleSheetTarget, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setContentsMargins(8, 0, 8, 0)
        self.setObjectName("streamer_widget")

        self.setStyleSheet(
            """
            #streamer_widget { border-bottom: 1px solid lightgray}
            """
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(42)
        self.status_lamp = QLabel()
        self.status_lamp.setFixedSize(8, 8)
        self.status_lamp.setContentsMargins(0, 0, 0, 0)
        self.status_lamp.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents, True
        )

        self.bjid_label = QLabel(self.bjid)
        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("color: red; font-size: 8pt;")
        self.progress_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
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
        self.hl.setContentsMargins(4, 2, 4, 2)
        self.hl.addWidget(self.status_lamp)
        self.hl.addWidget(self.bjid_label)
        self.hl.addStretch(1)
        self.hl.addWidget(self.progress_label)
        self.hl.addWidget(self.password_input)
        self.hl.addWidget(self.quality_spinbox)
        self.hl.addWidget(self.removeButton)

    def check(self, session: requests.Session):
        try:
            response = session.post(
                PLAYER_LIVE_API,
                data={
                    **API_DATA_COMMON,
                    "bid": self.bjid,
                    "type": "live",
                },
            )
            try:
                response.raise_for_status()
            except:
                self.logwriter.error(
                    f"Failed to check live status for {self.bjid}: {response.status_code}"
                )
                return
        except:
            pass

        try:
            chn: dict = response.json().get("CHANNEL", {})
        except:
            chn = {}
        bjnick = chn.get("BJNICK", "")
        title = chn.get("TITLE", "")
        rescode = chn.get("RESULT", ERROR)

        if rescode == AUTH_FAIL:  # 로그인 필요
            status = LiveStatus.LOGIN_REQUIRED
        elif rescode == ERROR:  # 에러
            status = LiveStatus.ERROR
        elif self.prev_rescode == OFFLINE and rescode != OFFLINE:  # 뱅온
            status = LiveStatus.BANGON
        elif self.prev_rescode != OFFLINE and rescode == OFFLINE:  # 뱅종
            status = LiveStatus.BANGJONG
        elif self.prev_rescode != OFFLINE and rescode != OFFLINE:  # 방송 지속
            status = LiveStatus.LIVE
        else:  # 방송 없음 지속
            status = LiveStatus.NOT_LIVE
        self.prev_rescode = rescode

        self._update_lamp(status)
        if status == LiveStatus.BANGON and not self.download_thread:
            path = get_unique_filename(
                os.path.join(
                    self.output_dir,
                    bjnick,
                    re.sub(
                        r'[\/:*?"<>|]', "", f"[{time.strftime('%Y%m%d')}]{title}.ts"
                    ),
                )
            ).replace("/", "\\")
            self._start_download(output_path=path)
        if status == LiveStatus.BANGJONG:
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
        self.logwriter.info(f"Starting download: {self.bjid}")
        self.logwriter.info(f"Output path: {output_path}")
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
            self.logwriter.warning(
                "Target Stream Not Found; using 'best' quality instead."
            )
            self.target_stream = streams.get("best", None)

        if not target_stream:
            self.logwriter.error("No valid stream found for the given quality.")
            return

        self.download_thread = download_thread(
            stream=target_stream, output_path=output_path
        )
        self.download_thread.start()
        self.progress_timer.start()

    def _stop_download(self):
        try:
            self.progress_timer.stop()
            self.progress_label.clear()
            self.logwriter.info(f"Stopping download: {self.bjid}")
            if (
                hasattr(self, "download_thread")
                and self.download_thread
                and self.download_thread.isRunning()
            ):
                self.download_thread.cleanup_sig.emit()
                self.download_thread = None
        except Exception as e:
            self.logwriter.error(f"Error stopping download for {self.bjid}: {e}")

    def update_progress(self):
        elapsed_time = time.time() - self.download_thread.init_time
        h = int(elapsed_time // 3600)
        m = int((elapsed_time % 3600) // 60)
        s = int(elapsed_time % 60)
        elapsed_time_str = f"{h:02}:{m:02}:{s:02}"
        tot_bytes_str = parse_byte_size(self.download_thread.total_bytes)
        self.progress_label.setText(f"{elapsed_time_str}\n{tot_bytes_str}")


class download_thread(QThread):
    power = True
    cleanup_sig = pyqtSignal()

    def __init__(self, stream: SoopHLSStream, output_path="output.ts"):
        super().__init__()
        self.stream = stream
        self.output_path = output_path
        self.cleanup_sig.connect(self.cleanup)
        self.total_bytes = 0
        self.init_time = 0

    def run(self):
        self.init_time = time.time()
        self.power = True
        streamreader = self.stream.open()
        if not os.path.exists(os.path.dirname(self.output_path)):
            os.makedirs(os.path.dirname(self.output_path))
        with open(self.output_path, "wb") as f:
            while True:
                if not self.power:
                    if not streamreader.closed:
                        streamreader.close()
                    break
                bytes = streamreader.read(8192)  # Read 8KB at a time
                if not bytes:
                    time.sleep(0.1)
                    continue
                f.write(bytes)
                self.total_bytes += len(bytes)

    def cleanup(self):
        self.power = False
        time.sleep(0.5)
