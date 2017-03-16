import sys
import os.path
from chameleon import PageTemplateLoader
from datetime import datetime
import xml.etree.ElementTree as elementTree

""" Resx2tmx
This converter relies on Chameleon. See: https://pypi.python.org/pypi/Chameleon
Installed with python -m pip install Chameleon

Assumes that the base language is English and will be in Resources.resx in same directory as the target.
"""

RESX2TMX_VERSION = 0.2
TEMPLATE_DIR = "templates"
TEMPLATE = "template.tmx"
TIMESTAMP_JSON_FORMAT = "%Y%m%dT%H%M%SZ"
RESX_DATA_NODE = "data"
RESX_VALUE_NODE = "value"
RESX_KEY = "name"
ENGLISH_LANG = "en"

class Document:
    def __init__(self, target_doc):
        self.datetime = datetime.now().strftime(TIMESTAMP_JSON_FORMAT)
        self.target_doc = os.path.abspath(target_doc)
        self.tool_version = RESX2TMX_VERSION

class TranslationItem:
    def __init__(self, src_lang, src_text, target_lang, target_text):
        self.source_lang = ENGLISH_LANG
        self.source_text = src_text
        self.target_lang = target_lang
        self.target_text = target_text


def read_source_items(resx_file):
    source_items = {}

    root = elementTree.parse(resx_file)
    for data_node in root.findall(RESX_DATA_NODE):
        key = data_node.get(RESX_KEY)
        value = data_node.find(RESX_VALUE_NODE).text
        source_items[key] = value

    return source_items


def main(target_lang_resx, out_tmx):
    print("Using {} to create a TMX file {}".format(target_lang_resx, out_tmx))

    if not os.path.exists(target_lang_resx):
        print("File '{}' does not exist.".format(target_lang_resx))
        return

    templates = PageTemplateLoader(os.path.abspath(TEMPLATE_DIR))
    tmx_template = templates[TEMPLATE]

    doc = Document(target_lang_resx)
    # todo parse the resx files :)
    item1 = TranslationItem("en","hello","fr","bonjour") 
    item2 = TranslationItem("en","what","fr","quoi") 
    trans_units = [item1, item2]

    print (tmx_template(items=trans_units, document = doc))
    src_items = read_source_items(target_lang_resx)

    #TODO: Deduce the English language res file from the supplied filename


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <target_lang_resx>".format(sys.argv[0]))
        exit()

    #TODO: Change this to take a directory and a target language
    target_lang_resx = sys.argv[1] if sys.argv[1] != "-" else r"./testdata/Resources.fr.resx"
    out_tmx = sys.argv[2] if sys.argv[2] != "-" else r"./testout/Translations.tmx"
    main(target_lang_resx, out_tmx)
