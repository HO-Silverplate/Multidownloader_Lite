from PyQt6.QtCore import pyqtSignal, QObject
import time

INFO_FORMAT = "[INFO][+{timestmp:08d}] {message}"
WARNING_FORMAT = "[WARN][+{timestmp:08d}] {message}"
ERROR_FORMAT = "[ERR][+{timestmp:08d}] {message}"


class LogWriter(QObject):
    msg_sig = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.init_time = time.time()

    def info(self, message: str):
        timestamp = int(time.time() - self.init_time)
        message = INFO_FORMAT.format(timestmp=timestamp, message=message)
        self.msg_sig.emit(message)

    def warning(self, message: str):
        timestamp = int(time.time() - self.init_time)
        message = WARNING_FORMAT.format(timestmp=timestamp, message=message)
        self.msg_sig.emit(message)

    def error(self, message: str):
        timestamp = int(time.time() - self.init_time)
        message = ERROR_FORMAT.format(timestmp=timestamp, message=message)
        self.msg_sig.emit(message)
