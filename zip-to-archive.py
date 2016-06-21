#!/usr/bin/env python3

import sys
import os
from subprocess import run
from shutil import rmtree
from time import time
from datetime import timedelta, datetime

"""Zip up each directory in the current folder as separate archives to a specified location (default hardcoded).
  The original directories will be deleted."""

_ZIP_OUTPUT_DIR = r"c:\Test\ZippedOutput"
_DEFAULT_MIN_DAYS_OLD = 100    # days


def calc_birth_date_from_age(days_old: int):
    """Returns a timestamp that is days_from_today in the past. Use negative value to go forwards."""
    delta = timedelta(days=days_old)
    return (datetime.today() - delta).timestamp()


def calc_age_from_modtime(modtime: int):
    delta = datetime.today().timestamp() - modtime/1e9
    return timedelta(seconds=delta).days


def get_latest_mod_date_in_dir(path):
    """Non-recursive most recent modification date determination. No directories included.
    Returned value is nanoseconds since epoch. If no files are found, returns date of the containing directory."""
    file_entries = filter(lambda f: f.is_file(), os.scandir(path))
    file_stats = [f.stat() for f in file_entries]

    try:
        return max(map(lambda s: s.st_mtime_ns, file_stats))

    except ValueError:
        # no entries
        dir_stat = os.stat(path)
        return dir_stat.st_mtime_ns


def main(zip_folder, min_days_old):
    if not (os.path.exists(zip_folder)):
        print("Error: Output folder '{0}' does not exist.".format(zip_folder))
        return

    cut_off_date_ns = int(calc_birth_date_from_age(min_days_old)*1e9)
    dirs = [d for d in os.listdir(".") if os.path.isdir(d)]

    for d in dirs:
        print(d)
        archive_name = os.path.join(zip_folder, "%s.7z" % d)

        if os.path.exists(archive_name):
            print("Error: Archive %s already exists. Skipping." % d)
            continue

        modtime = get_latest_mod_date_in_dir(d)
        if modtime > cut_off_date_ns:
            print("Skipping {}: only {} days old (less than {})."
                  .format(d, calc_age_from_modtime(modtime), min_days_old))
            continue

        zip_command = r'7z a "{0}" ".\{1}\*" -sdel -bso0'.format(archive_name, d)
        result = run(zip_command)

        if result.returncode == 0 and os.path.exists(archive_name):
            os.utime(archive_name, ns=(modtime, modtime))
            rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    _zip_folder = _ZIP_OUTPUT_DIR
    _min_days_old = _DEFAULT_MIN_DAYS_OLD

    if len(sys.argv) > 1:
        _zip_folder = sys.argv[1]

    if len(sys.argv) > 2:
        _min_days_old = int(sys.argv[2])

    print("zip folder: {}\nmin days old: {}".format(_zip_folder, _min_days_old))
    main(_zip_folder, _min_days_old)
    print("All done!")
