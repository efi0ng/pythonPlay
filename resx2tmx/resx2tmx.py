#!/usr/bin/env python3
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
ENG_RESX_FILE="Resources.resx"
RESX_FILE_FMT="Resources.{}.resx"
RESX_DATA_NODE = "data"
RESX_VALUE_NODE = "value"
RESX_KEY = "name"
ENGLISH_LANG = "en"

class Document:
    def __init__(self, target_doc):
        self.datetime = datetime.now().strftime(TIMESTAMP_JSON_FORMAT)
        self.target_doc = os.path.abspath(target_doc)
        self.tool_version = RESX2TMX_VERSION

class TranslationUnit:
    def __init__(self, src_lang, src_text, target_lang, target_text):
        self.source_lang = ENGLISH_LANG
        self.source_text = src_text
        self.target_lang = target_lang
        self.target_text = target_text


def read_resx_items(resx_file, dict_func):
    """For each item in resx file call dict_func(key, value)"""
    root = elementTree.parse(resx_file)
    for data_node in root.findall(RESX_DATA_NODE):
        key = data_node.get(RESX_KEY)
        value = data_node.find(RESX_VALUE_NODE).text
        dict_func(key,value)


def read_source(resx_file):
    source_items = {}
    def dict_func(key, value):
        source_items[key] = value

    read_resx_items(resx_file, dict_func)
    return source_items


def build_trans_units(source_items, target_lang, target_resx):
    trans_units = []
    def dict_func(key, value):
        if key in source_items and source_items[key] != value:
            tu = TranslationUnit(ENGLISH_LANG,source_items[key],target_lang,value)
            trans_units.append(tu)

    read_resx_items(target_resx, dict_func)
    return trans_units


def main(target_lang, res_folder, out_tmx):
    eng_resx = os.path.join(res_folder, ENG_RESX_FILE)
    target_resx = os.path.join(res_folder, RESX_FILE_FMT.format(target_lang))

    print("Using {} to create a TMX file {}".format(target_resx, out_tmx))

    if not os.path.exists(eng_resx):
        print("File '{}' does not exist.".format(eng_resx))
        return

    if not os.path.exists(target_resx):
        print("File '{}' does not exist.".format(target_resx))
        return

    templates = PageTemplateLoader(os.path.abspath(TEMPLATE_DIR))
    tmx_template = templates[TEMPLATE]

    doc = Document(target_resx)
    src_items = read_source(eng_resx)
    trans_units = build_trans_units(src_items, target_lang, target_resx)

    tmx_str = tmx_template(items=trans_units, document = doc)

    with open(out_tmx, 'w',encoding='utf8') as outfile:
        print(tmx_str, file=outfile)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: {} <target_lang> <res_folder> <out_tmx>".format(sys.argv[0]))
        exit()

    target_lang = sys.argv[1] if sys.argv[1] != "-" else "fr"
    res_folder = sys.argv[2] if sys.argv[2] != "-" else r"./testdata"
    out_tmx = sys.argv[3] if sys.argv[3] != "-" else r"./testout/Translations.tmx"
    main(target_lang, res_folder, out_tmx)
