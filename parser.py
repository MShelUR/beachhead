# -*- coding: utf-8 -*-
"""
A simple parser to interpret beachhead commands.
"""

###
# Credits
###

__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2022, University of Richmond'
__credits__ = None
__version__ = '0.1'
__maintainer__ = 'George Flanagin'
__email__ = 'gflanagin@richmond.edu'
__status__ = 'Teaching Example'
__license__ = 'MIT'

###
# Built in imports.
###

import os
import sys
__required_version__ = (3,8)
if sys.version_info < __required_version__:
    print(f"This code will not compile in Python < {__required_version__}")
    sys.exit(os.EX_SOFTWARE)

###
# Standard imports.
###
import calendar # for leap year.
import datetime # to resolve "now" and large offsets.

###
# Installed imports.
###
try:
    import parsec
except ImportError as e:
    print("stardate_parser requires parsec be installed.")
    sys.exit(os.EX_SOFTWARE)

###
# Project imports.
###
from parser_konstants import *

# These are the simple parsers and regexes.
eq              = lexeme(parsec.string(EQUAL))
comma           = lexeme(parsec.string(COMMA)) | WHITESPACE
null            = lexeme(parsec.string("(null)")).result(None)
na              = lexeme(parsec.string("N/A")).result(None)
ns              = lexeme(parsec.string("n/s")).result(None)
keyname         = lexeme(parsec.regex(r'[a-zA-Z]+'))

COMMANDS = frozenset(('open', 'close', 'run', 'log'))
OBJECTS = frozenset(('socket', 'session', 'transport')) 

@parsec.generate
def kv_pair() -> tuple:
    """
    In a general way, look for assignment statements.
    """
    key = yield keyname
    print(f"{key=}")
    yield eq
    value = yield ( timestamp() | 
        time() | 
        integer() | 
        number() | 
        null | 
        na | 
        ns | 
        linux_version | 
        charseq () )
    print(f"{value=}")
    yield comma

    return key, value


# And here is our parser in one line.
beachhead_parser = WHITESPACE >> parsec.many(kv_pair)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python slurmparser.py {text|filename}")
        sys.exit(os.EX_USAGE)

    try:
        text = open(sys.argv[1]).read()
    except:
        text = sys.argv[1]

    print(slurm_parse.parse(text))
    sys.exit(os.EX_OK)

