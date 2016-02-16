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
to inject repetitive data like column descriptions into (xml) metadata
documents from a source that can be created quickly and easily, like
a table (.csv etc.), or perhaps JSON, YAML, or other light weight
markup.

Approach: initial goal is injection of table column descriptions from
csv tables into ArcGIS and / or CSGDM xml already populated (by ArcMap
etc.) with general and geometry related information. However the
architecture is intended to be expandable for other targets (ISO19139,
ISO Feature Catalog) and sources (JSON, YAML etc.).

forgo use of lxml because it's hard to install in some restricted
environments

Terry Brown, Terry_N_Brown@yahoo.com, Mon Feb 15 21:20:33 2016
"""

import argparse
from copy import deepcopy
import csv
import os
from pprint import pprint
import sys
from xml.etree import ElementTree

KEY_ALIASES = {
    'entity_name': [
        'entity', 'table_name', 'table', 'layer'
    ],
    'attribute_name': ['attribute', 'field_name', 'field', 'column_name',
        'column', ],
    # need column_* versions of these?
    'attribute_definition': ['definition', 'description', ],
    'attribute_source': ['source', ],
    'attribute_type': ['type', ],
    'min': ['minimum', ],
    'max': ['maximum', ],
}
class HandlerBase(object):
    """HandlerBase - base class for base classes which collect
    registrations of subclasses to handle different inputs. Defines
    a metaclass to do subclass registration, and handle() to select
    a subclass.  Subclasses should redefine handle() to determine
    if they handle a particular input.
    """

    # handle registration of subclasses
    class __metaclass__(type):
        def __new__(meta, name, bases, class_dict):
            cls = type.__new__(meta, name, bases, class_dict)
            if name != 'HandlerBase':
                if hasattr(cls, '_generators'):
                    cls._generators.append(cls)
                else:
                    # base class, don't register
                    cls._generators = []
            return cls


    @classmethod
    def handle(cls, opt):
        """__call__ - return an appropriate subclass to handle things

        :param argparse Namespace opt: options
        :return: ContentGenerator subclass instance
        """

        for i in cls._generators:
            if i.handle(opt):
                return i(opt)

        raise TypeError("No handler found for input")

class ContainerParser(HandlerBase):
    """ContainerParser - Base class for handling containers (templates)
    """


    def __init__(self, opt):
        """
        :param argparse Namespace opt: options
        """
        self.opt = opt



class ContainerParserArcGIS(ContainerParser):
    """ContainerParserArcGIS - class for handling ArcGIS metadata XML
    """
    def entities(self, with_ele=True):
        """entities - list entities (feature classes, really) in template

        :param book with_ele: include link to Element in dom
        """

        entities = []
        for ele_entity in self.opt.dom.findall('.//eainfo/detailed'):
            entity = {
                'entity_name': ele_entity.findall('.//enttypl')[0].text,
                'attributes': [],
            }
            if with_ele:
                entity['_ELE'] = ele_entity

            entities.append(entity)
            for ele_attribute in ele_entity.findall('.//attr'):
                entity['attributes'].append({
                    'attribute_name': ele_attribute.findall('.//attrlabl')[0].text,
                })
                if with_ele:
                    entity['attributes'][-1]['_ELE'] = ele_attribute

        return entities
    @staticmethod
    def handle(opt):
        """handle - see if this subclass handles content in opt

        :param argparse Namespace opt: options
        :return: True / False
        :rtype: bool
        """

        return opt.dom.findall(".//Esri")
class ContentGenerator(HandlerBase):
    """ContainerParser - Base class for generating content from input
    """
    def __init__(self, opt):
        """
        :param argparse Namespace opt: options
        """
        self.opt = opt


class ContentGeneratorCSV(ContentGenerator):
    """ContentGeneratorCSV - read table attribute descriptions from .csv
    """
    def entities(self):
        """entities - return list of entities for this input, a (csv)
        table with rows describing fields.  The presence of a
        `entity_name` field (or its aliases, like `table`) indicates more
        than one entity described.
        """

        entities = []
        reader = csv.reader(open(self.opt.content))
        hdr = {i.lower():n for n,i in enumerate(next(reader))}
        for row in reader:
            # for table inputs describing multiple tables
            row_name = get_val(row, 'entity_name', hdr)
            if (not entities or
                get_val(entities[-1], 'entity_name') != row_name):
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
class ContentWriter(HandlerBase):
    """ContentWriter - write merged content
    """
def __init__(self, opt):
    """
    :param argparse Namespace opt: options
    """
    self.opt = opt


def add_content(dom, opt):
    """add_content - Update dom with content from opt.content

    :param ElementTree dom: template DOM
    :param argparse Namespace opt: options
    """

    pass
def do_update(old, new):
    """do_update - like dict.update(), but use canonical key names

    :param dict old: dict to update
    :param dict new: dict with new info.

    """

    for newkey in new:

        if newkey.lower() in KEY_ALIASES:
            old[newkey.lower()] = new[newkey]
            continue

        # check aliases
        for key,keys in KEY_ALIASES.items():
            if newkey.lower() in keys:
                old[key] = new[newkey]
                break
        else:
            old[newkey] = new[newkey]
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



def merge_content(old, new, names, sublists=None):
    """merge_content - merge data from content into data from template

    :param list old: elements (feature classes), or attributes
    :param lsit new: elements (feaures classes), or attributes
    :return: merged list
    """

    merged = deepcopy(old)
    to_append = []  # at end, not while iterating

    for i_new in new:
        found = False
        for i_old in merged:
            if get_val(i_old, names[0]) == get_val(i_new, names[0]):
                found = True
                if len(names) > 1:
                    i_old[sublists[1]] = merge_content(
                        i_old[sublists[1]], i_new[sublists[1]],
                        names[1:], sublists[1:])
                else:
                    do_update(i_old, i_new)
                break
        if found:
            break
        else:
            to_append.append(i_new)

    merged.extend(to_append)

    return merged
def main():
    """read args, load template, update, (over)write output"""
    opt = make_parser().parse_args()
    if opt.template:
        opt.dom = ElementTree.parse(opt.template)
    # add_content(dom, opt)
    if opt.output and os.file.exists(opt.output) and not opt.overwrite:
        raise IOError(
            "metapush: output file '%s' exists, --overwrite not specified" %
            out.output)

    if not opt.output:
        if opt.content:
            content = ContentGenerator.handle(opt).entities()
            # pprint(content)
        if opt.template:
            template = ContainerParser.handle(opt).entities(with_ele=False)
            # pprint(template)

        pprint(merge_content(
            template, content,
            ['entity_name', 'attribute_name'], [None, 'attributes']))
if __name__ == '__main__':
    main()
