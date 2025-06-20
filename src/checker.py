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
    code_dict:dict[str,str] = {}
    status_dict:dict[str, LiveStatus] = {}
    
    def _get_live_info(self, session: requests.Session, bjid: str) -> LiveStatus:
            response = session.post(
                PLAYER_LIVE_API,
                data={
                    **API_DATA_COMMON,
                    "bid": bjid,
                    "type": "live",
                },
            )
            try:
                response.raise_for_status()
            except Exception as e:
                return {"msg": f"Wrong Status from 'get_live_info': {e}"}
            
            self.code_dict[bjid]=0
            rescode:int = response.json().get("CHANNEL",{}).get("RESULT",{})
            prev_rescode:int = self.code_dict.get(bjid, -1)
            
            self.code_dict[bjid] = rescode
            if rescode == ResCode.AUTH_FAIL or rescode == ResCode.ERROR:  # 로그인 필요
                return LiveStatus.LOGIN_REQUIRED
            
            if prev_rescode == ResCode.OFFLINE and rescode != ResCode.OFFLINE:  # 뱅온
                return LiveStatus.BANGON
            elif prev_rescode != ResCode.OFFLINE and rescode == ResCode.OFFLINE:  # 뱅종
                return LiveStatus.BANGJONG
            elif prev_rescode and rescode != ResCode.OFFLINE:  # 방송 지속
                return LiveStatus.LIVE
            else:  # 방송 없음 지속
                return LiveStatus.NOT_LIVE
            
    def check_all(self, session: requests.Session):
        for bjid in self.code_dict.keys():
            self.status_dict[bjid] = self._get_live_info(session, bjid)
        return self.status_dict