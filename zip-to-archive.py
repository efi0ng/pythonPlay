#!/usr/bin/env python3
# Script version 2016.08.18.14.15

import sys
import os
from subprocess import run
from shutil import rmtree, copy2
from time import time
from datetime import timedelta, datetime
import gatherperfdata

"""Zip up each directory in the current folder as separate archives to a specified location (default hardcoded).
  The original directories will be deleted."""

_ZIP_OUTPUT_DIR = r"c:\Test\ZippedOutput"
_DEFAULT_MIN_DAYS_OLD = 100    # days
_DEFAULT_MAX_FILES_TO_ZIP = 30


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


def get_latest_mod_date_in_sub_dirs(path):
    """Use date of files one level beyond the given path to work out an age of the folder.
    If there are no sub-folders, fallback to using path."""
    dir_entries = list(filter(lambda f: f.is_dir(), os.scandir(path)))

    if len(dir_entries) == 0:
        return get_latest_mod_date_in_dir(path)

    return max(map(lambda f: get_latest_mod_date_in_dir(f.path), dir_entries))


def remove_pamir_backup_files(dir_name):
    test_dirs = [d for d in os.listdir(dir_name) if os.path.isdir(os.path.join(dir_name, d))]

    for test_dir in test_dirs:
        backup_folder = os.path.join(dir_name, test_dir, "data", "backup")
        if os.path.exists(backup_folder):
            print("Deleting backup folder: {}".format(backup_folder))
            rmtree(backup_folder, ignore_errors=True)


def try_gather_perf_data(test_folder):
    """Try to run the gatherperfdata script if it hasn't been run yet"""
    if os.path.exists(os.path.join(test_folder, "results.json")):
        return

    try:
        print("Gathering perf data for: {}".format(test_folder))
        gatherperfdata.main(test_folder)
    except FileNotFoundError as err:
        print(err)
    except IndexError as err:
        print(err)
    except KeyError as err:
        print(err)


def copy_result_json_to_archive_folder(zip_folder, test_run_folder, test_dir_name):
    """If a JSon file exists, copy it loose to the zip folder for ease of access."""
    json_file = os.path.join(test_run_folder, "results.json")
    try:
        if os.path.exists(json_file):
            # don't rename first since we want test folder contents untouched when archiving
            copy2(json_file, zip_folder)
            intermediate_file = os.path.join(zip_folder, "results.json")
            target_file = os.path.join(zip_folder, test_dir_name + ".results.json")
            os.rename(intermediate_file, target_file)
        else:
            print("Could not find json file: {}".format(json_file))
    except Exception as err:
        print(err)


def main(base_path, zip_folder, min_days_old, max_folders_to_zip=0):
    if not (os.path.exists(zip_folder)):
        print("Error: Output folder '{0}' does not exist.".format(zip_folder))
        return

    cwd = os.getcwd()
    gather_script_exists = os.path.exists(os.path.join(cwd, "gatherperfdata.py"))
    if gather_script_exists:
        print("Gather perf script found. Will run it on any folders that don't have result.json.")

    cut_off_date_ns = int(calc_birth_date_from_age(min_days_old)*1e9)
    dirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]

    total_files_zipped = 0
    
    for test_dir_name in dirs:
        archive_name = os.path.join(zip_folder, "%s.7z" % test_dir_name)

        if os.path.exists(archive_name):
            print("Error: Archive %s already exists. Skipping." % test_dir_name)
            continue

        cur_test_run_folder = os.path.join(base_path, test_dir_name)

        # regardless of age, we want to clean out backups from test folders
        remove_pamir_backup_files(cur_test_run_folder)

        # run data gatherer to be sure we've run it
        if gather_script_exists:
            try_gather_perf_data(cur_test_run_folder)

        modtime = get_latest_mod_date_in_sub_dirs(cur_test_run_folder)
        if modtime > cut_off_date_ns:
            print("Skipping {}: only {} days old (less than {})."
                  .format(test_dir_name, calc_age_from_modtime(modtime), min_days_old))
            continue

        # grab json result for easy access
        copy_result_json_to_archive_folder(zip_folder, cur_test_run_folder, test_dir_name)

        total_files_zipped += 1
        print("Zipping {}: {}".format(total_files_zipped, test_dir_name))
        zip_command = r'c:\Program Files\7-Zip\7z.exe a "{0}" "{1}\*" -sdel -bso0'\
            .format(archive_name, cur_test_run_folder)
        result = run(zip_command)

        if result.returncode == 0 and os.path.exists(archive_name):
            os.utime(archive_name, None, ns=(modtime, modtime))
            rmtree(cur_test_run_folder, ignore_errors=True)

        if 0 < max_folders_to_zip <= total_files_zipped:
            break

if __name__ == "__main__":
    _zip_folder = _ZIP_OUTPUT_DIR
    _min_days_old = _DEFAULT_MIN_DAYS_OLD
    _base_path = "."

    if len(sys.argv) > 1:
        if sys.argv[1] == "-h":
            print("zip-to-archive [source_folder] [dest_folder] [minimum_age]")
            exit()

        _base_path = sys.argv[1]
        if os.path.exists(_base_path):
            os.chdir(_base_path)

    else:
        _base_path = os.path.dirname(__file__)
        if _base_path != "":
            os.chdir(_base_path)
        else:
            _base_path = "."

    # avoid dangerous current working directory
    _cwd = os.getcwd()
    _max_files_to_zip = _DEFAULT_MAX_FILES_TO_ZIP
    if "windows" in _cwd:
        print("CWD contains the word Windows. Stopping now to avoid potentially serious side effects.")
        exit()

    if len(sys.argv) > 2:
        _zip_folder = sys.argv[2]

    if len(sys.argv) > 3:
        _min_days_old = int(sys.argv[3])

    if len(sys.argv) > 4:
        _max_files_to_zip = int(sys.argv[4])

    print("working folder: {}\nzip folder: {}\nmin days old: {}  | max files to zip: {}"
          .format(_cwd, _zip_folder, _min_days_old, _max_files_to_zip))
    main(_base_path, _zip_folder, _min_days_old, _max_files_to_zip)
    print("All done!")
