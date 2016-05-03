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

Forgo use of lxml because it's hard to install in some restricted
environments.

FIXME: do_update overwrites content with blanks, should it not do
that, or should user supply inputs in sensible order (populated
table first, then other). UPDATE: immediate problem was unordered
table / field lists in ContentGeneratorCSV.entities(), but this
issue still needs checking.

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
    'entity_definition': [
        'entity', 'table_name', 'table', 'layer'
    ],
    'attribute_name': ['attribute', 'field_name', 'field', 'column_name',
        'column', ],
    # need column_* versions of these?
    'attribute_definition': ['definition', 'description', ],
    'attribute_source': ['source', ],
    'attribute_type': ['type', 'storage'],
    'min': ['minimum', ],
    'max': ['maximum', ],
    'units': ['unit', ],
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
    def entities(self):
        """entities - list entities (feature classes, really) in template

        :param book with_ele: include link to Element in dom
        """

        entities = []
        for ele_entity in self.opt.dom.findall('.//eainfo/detailed'):
            entity = {
                'entity_name': ele_entity.findall('.//enttypl')[0].text,
                'attributes': [],
            }
            entities.append(entity)
            descrip = ele_entity.findall('.//enttypd')
            if descrip and descrip[0].text.strip():
                entity['entity_description'] = descrip[0].text.strip()

            if self.opt.no_template_attributes:
                continue

            for ele_attribute in ele_entity.findall('.//attr'):
                attribute = {
                    'attribute_name': ele_attribute.findall('.//attrlabl')[0].text,
                }
                entity['attributes'].append(attribute)
                for attrname, attrpath in [
                    ('min', 'attrdomv/rdom/rdommin'),
                    ('max', 'attrdomv/rdom/rdommax'),
                    ('units', 'attrdomv/rdom/attrunit'),
                    ('attribute_definition', 'attrdef'),
                ]:
                    attrval = ele_attribute.find(attrpath)
                    if attrval is not None:
                        attribute[attrname] = attrval.text

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
        ent2list = {}  # don't add dupes when source tables/fields unsorted
        reader = csv.reader(open(self.opt.content))
        hdr = {i.lower():n for n,i in enumerate(next(reader))}
        for row in reader:
            # for table inputs describing multiple tables
            row_name = get_val(row, 'entity_name', hdr)
            if (not entities or
                get_val(entities[using], 'entity_name') != row_name):
                if row_name not in ent2list:
                    entities.append({'entity_name': None, 'attributes': []})
                    entities[-1]['entity_name'] = row_name
                    ent2list[row_name] = len(entities) - 1
                using = ent2list[row_name]
            attributes = {k:row[hdr[k]] for k in hdr}
            attribute_name = get_val(attributes, 'attribute_name')
            if attribute_name:
                entities[using]['attributes'].append(attributes)
                # might just be a description of entities
            for k in hdr:
                if k.startswith('entity_') and row[hdr[k]].strip():
                    # harmlessly copies entity_name over entity_name, needed
                    # to copy entity_description in some contexts
                    entities[using][k] = row[hdr[k]].strip()

        if self.opt.tables:
            entities = [i for i in entities
                       if i['entity_name'] in self.opt.tables]

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



class ContentWriterArcGIS(ContentWriter):
    """ContentWriterArcGIS - write content to ESRI XML
    """
    @staticmethod
    def handle(opt):
        """handle - see if this subclass handles content in opt

        :param argparse Namespace opt: options
        :return: True / False
        :rtype: bool
        """

        return ContainerParserArcGIS.handle(opt)

    def write(self, content):
        """write - write content into opt.dom

        :param list content: merged content
        """

        for entity in content:
            ent_path = make_path(
                self.opt.dom.getroot(), 'eainfo/detailed', 'enttyp/enttypl',
                get_val(entity, 'entity_name')
            )

            entity_description = get_val(entity, 'entity_description')
            if entity_description and entity_description.strip():
                enttyp = ent_path[-1].find('enttyp')
                enttypd = enttyp.find('enttypd')
                if enttypd is None:
                    enttypd = ElementTree.Element('enttypd')
                    enttyp.append(enttypd)
                enttypd.text = entity_description

            detailed = ent_path[-1]
            for attribute in entity['attributes']:
                attr_path = make_path(
                    detailed, 'attr', 'attrlabl',
                    get_val(attribute, 'attribute_name')
                )
                attr = attr_path[-1]

                for attrname, attrpath in [
                    ('attribute_type', 'attrtype'),
                    ('attribute_definition', 'attrdef'),
                    ('min', 'attrdomv/rdom/rdommin'),
                    ('max', 'attrdomv/rdom/rdommax'),
                    ('units', 'attrdomv/rdom/attrunit'),
                ]:
                    attrval = get_val(attribute, attrname)
                    if attrval is not None and str(attrval).strip():
                        # 0 (zero) is a valid value
                        pos = attr
                        steps = attrpath.split('/')
                        while steps:
                            step = steps.pop(0)
                            if pos.find(step) is not None:
                                pos = pos.find(step)
                            else:
                                ele = ElementTree.Element(step)
                                pos.append(ele)
                                pos = ele
                        pos.text = attrval
def add_content(dom, opt):
    """add_content - Update dom with content from opt.content

    :param ElementTree dom: template DOM
    :param argparse Namespace opt: options
    """

    pass
def compare_data(opt, content):
    """compare_data - compare data found at opt.data with content,
    report difference in table and field sets

    currently targets .csv files in opt.data, should probably be an
    OGR source

    :param argparse Namespace opt: options
    :param list content: content assembled in main()
    """

    # re-arrange content as a dict
    content = {i['entity_name']:i['attributes'] for i in content}
    for key in list(content):
        content[key] = {get_val(i, 'attribute_name'):i for i in content[key]}

    # search opt.data for .csv files
    data = find_data(opt)

    # look for tables / files without metadata
    for table, fields in data.items():
        if table not in content:
            print "Data table '%s' not in metadata" % (table)
            continue
        for field in fields:
            if field not in content[table]:
                print "Data field '%s.%s' not in metadata" % (table, field)

    # look for metadata without tables / fields in data
    for table, fields in content.items():
        if table not in data:
            print "Table metadata '%s' not in data" % (table)
            continue
        for field in fields:
            if field not in data[table]:
                print "Field metadata '%s.%s' not in data" % (table, field)
def do_update(old, new):
    """do_update - like dict.update(), but use canonical key names

    #X Also, don't process keys with non-scalar values

    :param dict old: dict to update
    :param dict new: dict with new info.

    """

    for newkey in new:

        if not isinstance(new[newkey], (str, unicode)):
            continue

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
def find_data(opt):
    data = {}
    if opt.data is None:
        return data
    for path, dirs, files in os.walk(opt.data):
        for file_ in files:
            if file_.lower().endswith(".csv"):
                filepath = os.path.join(path, file_)
                reader = csv.reader(open(filepath))
                data[file_[:-4]] = next(reader)
                ## row_count = 0
                ## for i in reader:
                ##     row_count += 1
                ## data[file_[:-4]+':row_count'] = str(row_count)
    return data
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
    parser.add_argument('--content', nargs='+',
        help="content (field descriptions) to push into metadata")
    parser.add_argument('--output', help="output file")
    parser.add_argument("--overwrite", action='store_true',
        help="overwrite output if it exists"
    )

    parser.add_argument('--tables', nargs='+',
        help="if `content` covers multiple tables, use only these")
    parser.add_argument('--data',
        help="path (e.g. '.') on which to find data, will check for "
             "mismatch in tables / fields with metadata)")
    parser.add_argument('--missing-content',
        help="extend (or create) the file used with --content "
             "to include missing info. based on --data", metavar='FILE')

    parser.add_argument('--no-template-attributes', action='store_true',
        help="ignore (and drop) all attribute level metadata in template")

    return parser
def make_path(dom, path, textpath, text):
    """make_path - find or make a path of XML elements ending
    in one with `text` as its text content (maybe in a subpath) e.g.:

    call: dom, 'eainfo/detailed', 'enttyp/enttypl', 'MyTable'

    returns: [<Element:eainfo>, <Element:datailed>]

    such that the `detailed` element has a child `enttyp` which has a child
    `enttypl` with text 'MyTable'

    :param XML dom: XML to search / edit
    :param str path: XPath like path to target container
    :param str textpath: more XPath like path to element containing name
    :param str text: text (name) to place in last element
    """

    steps = path.split('/')
    path = [dom]
    while steps:
        step = steps.pop(0)
        next = path[-1].findall('.//'+step)
        if not steps:
            break  # next is list of possibles
        if next:
            assert len(next) == 1, path
            path.append(next[0])
        else:  # add intermediates if needed
            ele = ElementTree.Element(step)
            path[-1].append(ele)
            path.append(ele)
    # end with `next` list of possibles

    for test in next:
        if textpath:
            src = test.findall(textpath)
            assert len(src) == 1, (src, path, next, textpath)
            value = src[0].text
        else:
            value = test.text
        if value == text:
            path.append(test)
            break
    else:
        text_holder = ElementTree.Element(step)
        path[-1].append(text_holder)
        path.append(text_holder)
        for step in textpath.split('/'):
            new = ElementTree.Element(step)
            text_holder.append(new)
            text_holder = new
        new.text = text

    return path
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
                do_update(i_old, i_new)  # scalar values only
                if len(names) > 1:
                    i_old[sublists[1]] = merge_content(
                        i_old[sublists[1]], i_new[sublists[1]],
                        names[1:], sublists[1:])
                break
        if not found:
            to_append.append(i_new)

    merged.extend(to_append)

    return merged
def missing_content(opt, content):
    """missing_content - make table for --content for missing info.

    :param argparse Namespace opt: options
    :param content: existing content, to extend
    """

    # re-arrange content as a dict, COPIED from compare_data()
    full_content = content  # save for entity descriptions below
    content = {i['entity_name']:i['attributes'] for i in content}
    for key in list(content):
        content[key] = {get_val(i, 'attribute_name'):i for i in content[key]}

    # search opt.data for .csv files
    data = find_data(opt)

    # look for tables / files without metadata
    for table, fields in data.items():
        if table not in content:
            content[table] = {}  # a this *table* to metadata collection
        # work out which metadata field names are in use
        metafields = set()
        for records in content[table].values():
            metafields.update(records.keys())
        for field in fields:
            if field not in content[table]:
                fieldinfo = {}
                content[table][field] = fieldinfo
                for key in KEY_ALIASES:
                    if key.startswith('entity_'):
                        continue
                    set_val(key, metafields, fieldinfo, '')
                set_val('attribute_name', metafields, fieldinfo, field)

    # now write out the --content table again
    metafields = set()
    for entity_name, table in content.items():
        for fieldinfo in table.values():
            metafields.update(fieldinfo.keys())

    metafields = [i for i in metafields if not i.startswith("entity_")]
    writer = csv.writer(open(opt.missing_content, 'wb'))
    writer.writerow(['entity_name']+metafields)
    for table, fields in content.items():
        for field in fields.values():
            row = [table] + [field.get(k) for k in metafields]
            writer.writerow(row)
    # write out entity descriptions
    missing_ents = "%s_ents.%s" % tuple(opt.missing_content.rsplit('.', 1))
    writer = csv.writer(open(missing_ents, 'wb'))
    writer.writerow(['entity_name', 'entity_description'])
    for entity in full_content:
        row = [
            (get_val(entity, i) or '')
            for i in ('entity_name', 'entity_description')]
        # could be ascii/utf-8 OR CP-1252
        for n in range(len(row)):
            try:
                row[n] = row[n].encode('utf-8')
            except UnicodeDecodeError:
                row[n] = row[n].decode('windows-1252').encode('utf-8')
        writer.writerow(row)
def set_val(key, metafields, fieldinfo, value):
    """
    set_val - set a value in a dict of field metadata, using
    aliases from KEY_ALIASES if they're already in metafields

    :param str key: the key to set
    :param set(str) metafields: fields already in use
    :param dict fieldinfo: dict to add key:value too
    :param str value: value to add
    """

    for alias in metafields:
        if alias in KEY_ALIASES[key]:
            key = alias
            break
    fieldinfo[key] = value

def main():
    """read args, load template, update, (over)write output"""
    opt = make_parser().parse_args()
    if opt.template:
        opt.dom = ElementTree.parse(opt.template)
    # add_content(dom, opt)
    if opt.output and os.path.exists(opt.output) and not opt.overwrite:
        raise IOError(
            "metapush: output file '%s' exists, --overwrite not specified" %
            opt.output)

    content = None
    template = None
    merged = None
    datasets = []  # may contain any or all of info. from template,
                   # info. from content, and those two merged

    if opt.template:
        template = ContainerParser.handle(opt).entities()
        datasets.append(template)
    if opt.content:
        content = []
        for file_ in opt.content:
            opt.content = file_
            subcontent = ContentGenerator.handle(opt).entities()
            content = merge_content(content, subcontent,
                ['entity_name', 'attribute_name'], [None, 'attributes'])
        datasets.append(content)
    if opt.template and opt.content:
        merged = merge_content(template, content,
            ['entity_name', 'attribute_name'], [None, 'attributes'])
        datasets.append(merged)

    if opt.data and datasets:
        compare_data(opt, datasets[-1] if datasets else [])
        # datasets[-1] will be merged info., or content info., or
        # template info., in that order of preference based on availability

    if opt.missing_content:
        # if not opt.data:
        #     print("--missing-content makes no sense without --data")
        #     exit(10)
        missing_content(opt, datasets[-1] if datasets else [])

    if opt.output:

        if not opt.template:
            print "Can't use --output without --template"
            exit(10)

        # content from template
        template = ContainerParser.handle(opt).entities()
        # new content
        content = ContentGenerator.handle(opt).entities()

        writer = ContentWriter.handle(opt)
        writer.write(merged)
        opt.dom.write(open(opt.output, 'wb'), encoding='utf-8')

        return

    if not opt.missing_content:
        pprint(datasets[-1])
        print("Didn't find anything to do")


if __name__ == '__main__':
    main()
