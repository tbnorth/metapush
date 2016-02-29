# metapush

Push content into metadata files

See docs. at top of [metapush.py](metapush.py) for more info.

    usage: metapush.py [-h] [--template TEMPLATE]
                       [--content CONTENT [CONTENT ...]] [--output OUTPUT]
                       [--overwrite] [--tables TABLES [TABLES ...]] [--data DATA]
                       [--no-template-attributes]

    Push content into metadata files efficiently

    optional arguments:
      -h, --help            show this help message and exit
      --template TEMPLATE   metadata template (default: None)
      --content CONTENT [CONTENT ...]
                            content (field descriptions) to push into metadata
                            (default: None)
      --output OUTPUT       output file (default: None)
      --overwrite           overwrite output if it exists (default: False)
      --tables TABLES [TABLES ...]
                            if `content` covers multiple tables, use only these
                            (default: None)
      --data DATA           path (e.g. '.') on which to find data, will check for
                            mismatch in tables / fields with metadata) (default:
                            None)
      --no-template-attributes
                            ignore (and drop) all attribute level metadata in
                            template (default: False)

