import sys
import os.path


def main(target_lang_resx, out_tmx):
    # todo: write intelligent code here
    print("Using {} to create a TMX file {}".format(target_lang_resx, out_tmx))

    if not os.path.exists(target_lang_resx):
        print("File '{}' does not exist.".format(target_lang_resx))
        return




if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <target_lang_resx>".format(sys.argv[0]))
        exit()

    target_lang_resx = sys.argv[1] if sys.argv[1] != "-" else r"./testdata/Resources.fr.resx"
    out_tmx = sys.argv[2] if sys.argv[2] != "-" else r"./testout/Translations.tmx"
    main(target_lang_resx, out_tmx)
