# -*- coding: utf-8 -*-
import typing
from   typing import *

min_py = (3, 8)

###
# Standard imports, starting with os and sys
###
import os
import sys
if sys.version_info < min_py:
    print(f"This program requires Python {min_py[0]}.{min_py[1]}, or higher.")
    sys.exit(os.EX_SOFTWARE)

from   collections.abc import Iterable
import importlib.util
###
# Credits
###
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2022'
__credits__ = None
__version__ = 0.1
__maintainer__ = 'George Flanagin'
__email__ = ['gflanagin@richmond.edu', 'me@georgeflanagin.com']
__status__ = 'in progress'
__license__ = 'MIT'

def all_installed(required_modules:Iterable) -> tuple:
    """
    required_items -- a list of some kind that names modules that 
        must be installed for the caller to proceed.

    returns -- a tuple with one of the os.EX_* symbols and
        a possibly empty set of missing modules. 
    """

    missing_modules = set()
    for _ in required_modules:
        try:
            if not importlib.util.find_spec(_): 
                missing_modules.add(_)
        except Exception as e:
            missing_modules.add(_)

    return os.EX_SOFTWARE if len(missing_modules) else os.EX_OK, missing_modules

