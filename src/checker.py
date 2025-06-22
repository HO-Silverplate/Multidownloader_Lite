import requests
from enum import Enum

PLAYER_LIVE_API = "https://live.sooplive.co.kr/afreeca/player_live_api.php"

API_DATA_COMMON = {
    "from_api": "0",
    "mode": "landing",
    "player_type": "html5",
    "stream_type": "common",
}


class ResCode(Enum):
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


class Checker:
    prev_rescode: int

    def __init__(self, bjid):
        self.bjid = bjid

    def check(self, session: requests.Session, bjid: str) -> tuple[LiveStatus, str]:
        response = session.post(
            PLAYER_LIVE_API,
            data={
                **API_DATA_COMMON,
                "bid": bjid,
                "type": "live",
            },
        )
        response.raise_for_status()

        rescode: int = response.json().get("CHANNEL", {}).get("RESULT", {})

        if rescode == ResCode.AUTH_FAIL or rescode == ResCode.ERROR:  # 로그인 필요
            status = LiveStatus.LOGIN_REQUIRED

        if self.prev_rescode == ResCode.OFFLINE and rescode != ResCode.OFFLINE:  # 뱅온
            status = LiveStatus.BANGON
        elif (
            self.prev_rescode != ResCode.OFFLINE and rescode == ResCode.OFFLINE
        ):  # 뱅종
            status = LiveStatus.BANGJONG
        elif self.prev_rescode and rescode != ResCode.OFFLINE:  # 방송 지속
            status = LiveStatus.LIVE
        else:  # 방송 없음 지속
            status = LiveStatus.NOT_LIVE

        title = response.json().get("CHANNEL", {}).get("TITLE", "")

        self.prev_rescode = rescode
        return status, title
