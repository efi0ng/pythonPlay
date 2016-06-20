#!/usr/bin/env python3

import sys
import os
from subprocess import run
from shutil import rmtree
from time import time

"""Zip up each directory in the current folder as separate archives to a specified location (default hardcoded).
  The original directories will be deleted."""

_ZIP_OUTPUT_DIR = r"c:\Test\ZippedOutput"


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


def main(zip_folder):
    if not (os.path.exists(zip_folder)):
        print("Error: Output folder '{0}' does not exist.".format(zip_folder))
        return

    dirs = [d for d in os.listdir(".") if os.path.isdir(d)]

    for d in dirs:
        print(d)
        archive_name = os.path.join(zip_folder, "%s.7z" % d)

        if os.path.exists(archive_name):
            print("Error: Archive %s already exists. Skipping." % d)
            continue

        mod_time = get_latest_mod_date_in_dir(d)
        zip_command = r'7z a "{0}" ".\{1}\*" -sdel'.format(archive_name, d)
        result = run(zip_command)

        if result.returncode == 0 and os.path.exists(archive_name):
            os.utime(archive_name, ns=(mod_time, mod_time))
            rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    _zip_folder = _ZIP_OUTPUT_DIR
    if len(sys.argv) > 1:
        _zip_folder = sys.argv[1]
        print("zip folder: {}" .format(_zip_folder))

    main(_zip_folder)
