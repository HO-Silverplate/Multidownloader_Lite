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


def get_unique_filename(file_path: str) -> str:
    directory, filename = os.path.split(file_path)
    name, ext = os.path.splitext(filename)

    name = escape_filename(name)

    # 중복되지 않는 파일 경로를 찾기
    counter = 1
    unique_path = file_path
    while os.path.exists(unique_path):
        unique_path = os.path.join(directory, f"{name}({counter}){ext}")
        counter += 1

    return unique_path


def parse_byte_size(size: int):
    if size < 1024:
        return f"{size} B"
    elif size < 1024**2:
        return f"{size / 1024:.2f} KB"
    elif size < 1024**3:
        return f"{size / (1024 ** 2):.2f} MB"
    elif size < 1024**4:
        return f"{size / (1024 ** 3):.2f} GB"
    else:
        return f"{size / (1024 ** 4):.2f} TB"
