import json
import os
import platform
import shutil
import typing as t
from datetime import datetime
from pathlib import Path


def read_json(file) -> t.Any:
    try:
        with open(file, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        print(e)
        return None


def write_json(file, content) -> None:
    try:
        with open(file, 'w') as f:
            json.dump(content, f, indent=4)
    except Exception as e:
        print(e)


def get_args(args) -> t.List[str]:
    parameters = []
    idx = 0
    for arg in args:
        if idx == 0 and '--' not in arg:
            pass
        elif '--' in arg:
            parameters.append(rf'{arg}')
            idx += 1
        else:
            parameters[idx - 1] = parameters[idx - 1] + ' ' + rf'{arg}'

    return parameters


def get_readable_size(size: int, precision=2) -> str:
    if size is None:
        return ""

    suffixes = ['B', 'KB', 'MB', 'GB', 'TB']
    suffixIndex = 0
    while size >= 1024 and suffixIndex < len(suffixes):
        suffixIndex += 1  # increment the index of the suffix
        size = size / 1024.0  # apply the division
    return "%.*f%s" % (precision, size, suffixes[suffixIndex])


def get_file_last_modified_time(path_to_file: str) -> datetime:
    if path_to_file is None:
        return datetime.now()

    if platform.system() == "Windows":
        return datetime.fromtimestamp(os.path.getmtime(path_to_file))
    else:
        stat = os.stat(path_to_file)
        return datetime.fromtimestamp(stat.st_mtime)


def get_not_found_image_url() -> str:
    return "https://msdn.miaoshouai.com/msdn/userimage/not-found.svg"


def get_user_temp_dir() -> str:
    return os.path.join(Path.home().absolute(), ".miaoshou_assistant_download")


def assert_user_temp_dir() -> None:
    os.makedirs(get_user_temp_dir(), exist_ok=True)


def move_file(src: str, dst: str) -> None:
    if not src or not dst:
        return

    if not os.path.exists(src):
        return

    if os.path.exists(dst):
        os.remove(dst)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(src, dst)
