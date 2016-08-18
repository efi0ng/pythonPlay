"""Script to delete old builds - at least that was the original intention.
There will be cut-n-paste in here from zip-to-archive for the time being.
One day we may refactor to have a set of utils that are used for in house
system admin tasks
"""
import os
import sys
from datetime import datetime, timedelta

_KEEP_MARKER = "keep"
_DEFAULT_MIN_DAYS_OLD = 100

def calc_birth_date_from_age(days_old: int):
    """Returns a timestamp that is days_from_today in the past. Use negative value to go forwards."""
    delta = timedelta(days=days_old)
    return (datetime.today() - delta).timestamp()


def calc_age_from_modtime(modtime: int):
    """calculate age from the supplied modification time"""
    delta = datetime.today().timestamp() - modtime/1e9
    return timedelta(seconds=delta).days


def calc_file_age(dir_entry):
    """Given a DirEntry returned by os.scandir, provide the files age in days."""
    return calc_age_from_modtime(dir_entry.stat().st_mtime_ns)


def delete_old_builds(base_path, min_days_old):
    if not os.path.exists(base_path):
        print("Folder does not exist: {}".format(base_path))
        return

    files = filter(lambda f: not f.is_dir() and _KEEP_MARKER not in f.name.lower(), os.scandir(base_path))
    old_files = filter(lambda f: calc_file_age(f) >= min_days_old, files)
    for file in old_files:
        print("Deleting: {}  [Age {}]".format(file.name, calc_file_age(file)))
        os.remove(file.path)


def print_help_then_exit():
    print("delete-old-files path [minimum_age]")
    exit()


if __name__ == "__main__":
    _min_days_old = _DEFAULT_MIN_DAYS_OLD
    _base_path = "."

    if len(sys.argv) > 1:
        if sys.argv[1] == "-h":
            print_help_then_exit()

        _base_path = sys.argv[1]
        if not os.path.exists(_base_path):
            print("Path {} does not exist. Exiting.".format(_base_path))
            exit()

    else:
        print_help_then_exit()

    # avoid dangerous current working directory
    _cwd = os.getcwd()

    if "windows" in _cwd:
        print("working directory contains the word Windows. Stopping now to avoid potentially serious side effects.")
        exit()

    if len(sys.argv) > 2:
        _min_days_old = int(sys.argv[2])

    print("working folder: {}\nmin days old: {}"
          .format(_base_path, _min_days_old))
    delete_old_builds(_base_path, _min_days_old)
    print("All done!")
