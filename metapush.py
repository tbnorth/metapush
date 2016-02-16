"""
metapush.py - push content into metadata files efficiently

Problem: metadata editors, such as ArcGIS, Morpho, CatMDEdit, and
GeoNetwork, tend to be labor intensive, particularly when describing
repeated components such as columns in (attribute) tables. Column
definitions are often the piece of metadata people need first. Labor
here refers to a lot of pointing and clicking to add, expand, and fill
in hierarchical entry forms.

Solution: not another metadata editor, although it seems there's room
for one which focuses on efficiency and labor reduction, but a tool
to inject repeditive data like column descriptions into (xml) metadata
documents from a source that can be created quickly and easily, like
a table (.csv etc.), or perhaps JSON, YAML, or other light weight
markup.

Approach: initial goal is injection of table column descriptions from
csv tables into ArcGIS and / or CSGDM xml already populated (by ArcMap
etc.) with general and geometry related information. However the
archetecture is intended to be expandable for other targets (ISO19139,
ISO Feature Catalog) and sources (JSON, YAML etc.).


forgo use of lxml because it's hard to install in some restricted
environments

Terry Brown, Terry_N_Brown@yahoo.com, Mon Feb 15 21:20:33 2016
"""

import argparse
import csv
import os
from pprint import pprint
import sys
from xml.etree import ElementTree

KEY_ALIASES = {
    'entity_name': [
        'entity', 'table_name', 'table', 'layer'
    ],
    'attribute_name': [
        'attribute', 'field_name', 'field', 'column_name', 'column',
    ],
}
class ContentGenerator(object):
    """ContentGenerator - Base class for generating content from input
    """

    # handle registration of subclasses
    class __metaclass__(type):
        def __new__(meta, name, bases, class_dict):
            cls = type.__new__(meta, name, bases, class_dict)
            if hasattr(cls, '_generators'):
                cls._generators.append(cls)
            else:
                # base class, don't register
                cls._generators = []
            return cls

    @classmethod
    def handle(cls, opt):
        """__call__ - returna appropriate content generator

        :param argparse Namespace opt: options
        :return: ContentGenerator subclass instance
        """

        for i in cls._generators:
            if i.handle(opt):
                return i(opt)
    @staticmethod
    def get_val(source, key, hdr=None):
        """get_val - get a value from source with aliases

        :param dict/list source: source of values
        :param str key: key or alias to get
        :param dict hdr: map column numbers to key names
        """

        if hdr:
            source = {key:source[col] for key,col in hdr.items()}

        if key in source:
            # give exact match precedence
            return source[key]

        # check aliases
        keys = KEY_ALIASES.get(key, [])
        for key in keys:
            if key in source:
                return source[key]

        return None

class ContentGeneratorCSV(ContentGenerator):
    """ContentGeneratorCSV - read table attribute descriptions from .csv
    """
    def __init__(self, opt):
        """
        :param argparse Namespace opt: options
        """
        self.opt = opt


    def entities(self):
        """entities - return list of entities for this input, a (csv)
        table with rows describing fields.  The presence of a
        `entity_name` field (or its aliases, like `table) indicates more
        than one entity described.
        """

        entities = []
        reader = csv.reader(open(self.opt.content))
        hdr = {i:n for n,i in enumerate(next(reader))}
        for row in reader:
            # for table inputs describing multiple tables
            row_name = self.get_val(row, 'entity_name', hdr)
            if (not entities or
                self.get_val(entities[-1], 'entity_name') != row_name):
                entities.append({'entity_name': None, 'attributes': []})
                entities[-1]['entity_name'] = row_name

            entities[-1]['attributes'].append({k:row[hdr[k]] for k in hdr})

        return entities
    @staticmethod
    def handle(opt):
        """handle - see if this subclass handles content in opt

        :param argparse Namespace opt: options
        :return: True / False
        :rtype: bool
        """

        return (opt.content or '').lower().endswith('.csv')
def add_content(dom, opt):
    """add_content - Update dom with content from opt.content

    :param ElementTree dom: template DOM
    :param argparse Namespace opt: options
    """

    pass
def make_parser():

     parser = argparse.ArgumentParser(
         description="""Push content into metadata files efficiently""",
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
     )

     parser.add_argument('--template', help="metadata template")
     parser.add_argument('--content', help="content to push into metadata")
     parser.add_argument('--output', help="output file")
     parser.add_argument("--overwrite", action='store_true',
         help="overwrite output if it exists"
     )

     return parser



def main():
    """read args, load template, update, (over)write output"""
    opt = make_parser().parse_args()
    if opt.template:
        dom = ElementTree.parse(opt.template)
    # add_content(dom, opt)
    if opt.output and os.file.exists(opt.output) and not opt.overwrite:
        raise IOError(
            "metapush: output file '%s' exists, --overwrite not specified" %
            out.output)
    if opt.content:
        entities = ContentGenerator.handle(opt).entities()
        pprint(entities)
    # dom.write(opt.output)
if __name__ == '__main__':
    main()
