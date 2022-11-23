import os.path
from pathlib import Path

cwd = Path()


def path_to_str(path: Path):
    return path.relative_to().as_posix()


def str_to_path(str_path: str):
    return Path(str_path).relative_to(cwd)


def subdir_of_workdir(path: Path):
    return cwd in path.parents


def complain_if_not_in_cwd(path: Path):
    if not subdir_of_workdir(path) and path != cwd:
        raise ValueError(f'{path} is not in cwd ({cwd})')


def write_file(path: Path):
    with open(path, 'w+'):
        return path.read_text()


def path_edited_on(path: Path):
    try:
        return path.lstat().st_mtime
    except FileNotFoundError:
        return -1
