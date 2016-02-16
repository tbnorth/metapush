"""
metapush.py - push content to metadata files efficiently

Terry Brown, Terry_N_Brown@yahoo.com, Mon Feb 15 21:20:33 2016
"""

import argparse
import os
import sys
from xml.etree import ElementTree
# skip use of lxml because it's hard to install in some restricted environments

def add_content(dom, opt):
    """add_content - Update dom with content from opt.content

    :param ElementTree dom: template DOM
    :param argparse Namespace opt: options
    """

    pass
def make_parser():
     
     parser = argparse.ArgumentParser(
         description="""Push content to metadata files efficiently""",
         formatter_class=argparse.ArgumentDefaultsHelpFormatter
     )
     
     parser.add_argument('template', help="metadata template (XML)")
     parser.add_argument('content', help="content to push into metadata")
     parser.add_argument('output', help="output file")
     parser.add_argument("--overwrite", action='store_true',
         help="overwrite output if it exists"
     )

     return parser
 
 

def main():
    """read args, load template, update, (over)write output"""
    opt = make_parser().parse_args()
    dom = ElementTree.parse(opt.template)
    add_content(dom, opt)
    if os.file.exists(opt.output) and not opt.overwrite:
        raise IOError(
            "metapush: output file '%s' exists, --overwrite not specified" %
            out.output)
    dom.write(opt.output)
if __name__ == '__main__':
    main()
