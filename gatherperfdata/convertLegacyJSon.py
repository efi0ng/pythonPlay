#!/usr/bin/env python3

import sys
import os.path
import json
from gatherperfdata import JSonLabels, OpLabels, _TEST_SUITE_LABEL
import re

def treat_build_number(data, source_file):
    """Look for and correct build version missing."""
    build_tested = data[JSonLabels.BUILD_TESTED]
    if (build_tested[JSonLabels.REVISION] > 0
        and build_tested[JSonLabels.VERSION_SHORT] != ""):
        return

    REGEX = r"r([0-9]+).*?v([0-9.]+)"
    match = re.search(REGEX, source_file) 
    if match is None:
        print("Could not fix build num for: {}".format(source_file), sys.stderr)
        return

    rev = int(match.group(1))
    ver = match.group(2)
    build_tested[JSonLabels.REVISION] = rev
    build_tested[JSonLabels.VERSION_SHORT] = ver
    build_tested[JSonLabels.VERSION_LONG] = ver
    

def treat_suite_label(data):
    """Changes old TestComplete to the new label"""
    if data[JSonLabels.TEST_SUITE_LABEL] != "TestComplete":
        return

    data[JSonLabels.TEST_SUITE_LABEL] = _TEST_SUITE_LABEL


def treat_op_structure(data):
    """This will convert old format duration/filesize to new."""
    test_results = data[JSonLabels.TEST_RESULTS]
    if len(test_results) == 0:
        return

    op_results  = test_results[0][JSonLabels.OP_RESULTS]
    if len(op_results) == 0:
        return

    
    return


def treat_basic_avg_ops(data):
    """This will recalculate the averages in ms."""
    return



    
def main(source_path, target_path):
    print("Converting files in {}. Output to {}".format(source_path, target_path))

    if not os.path.exists(source_path):
        print("Folder '{}' does not exist.".format(source_path))
        return

    if not os.path.exists(target_path):
        print("Folder '{}' does not exist.".format(target_path))
        return


    source_files = [name for name in os.listdir(source_path)
                   if os.path.isfile(os.path.join(source_path, name)) and name.endswith(".json")]

    for source_file in source_files:
        current_filepath = os.path.join(source_path, source_file)
        target_filepath = os.path.join(target_path, source_file)
        with open(current_filepath, 'r') as f:
            data = json.load(f)

        treat_build_number(data, source_file)
        treat_suite_label(data)
        treat_op_structure(data)
        treat_basic_avg_ops(data)
        
        with open(target_filepath, 'w') as f:
            json.dump(data, f, indent=3, sort_keys=True)

            
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <source_path> <target_path>".format(sys.argv[0]))
        exit()

    source_p = sys.argv[1] if sys.argv[1] != "-" else r"./jcv_test/legacy"
    target_p = sys.argv[2] if sys.argv[2] != "-" else r"./jcv_test/converted"

    main(source_p, target_p)
