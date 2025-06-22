import os
import re
import sys


def escape_filename(s: str) -> str:
    return re.sub(r"[/\\?%*:|\"<>.\n{}]", "", s)


def truncate_long_name(s: str) -> str:
    return (s[:75] + "..") if len(s) > 77 else s


def resource_path(relpath) -> str:
    try:
        abspath = sys._MEIPASS  # type: ignore
    except Exception:
        abspath = os.path.abspath(".")
    return os.path.join(abspath, relpath).replace("\\", "//")
