import sys
import os.path
import json
from gatherperfdata import JSonLabels, OpLabels


def main(source_path, target_path):
    # todo: write intelligent code here
    print("Converting files in {}. Output to {}".format(source_path, target_path))

    if not os.path.exists(source_path):
        print("Folder '{}' does not exist.".format(source_path))
        return

    if not os.path.exists(target_path):
        print("Folder '{}' does not exist.".format(target_path))
        return


    source_files = [name for name in os.listdir(source_path)
                   if os.path.isfile(os.path.join(source_path, name)) and name.endswith(".json")]

    #print(source_files)

    for source_file in source_files:
        current_filepath = os.path.join(source_path, source_file)
        target_filepath = os.path.join(target_path, source_file)
        with open(current_filepath, 'r') as f:
            data = json.load(f)
            print(data[JSonLabels.BUILD_TESTED])


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <source_path> <target_path>".format(sys.argv[0]))
        exit()

    source_p = sys.argv[1] if sys.argv[1] != "-" else r"./jcv_test/legacy"
    target_p = sys.argv[2] if sys.argv[2] != "-" else r"./jcv_test/converted"

    main(source_p, target_p)
