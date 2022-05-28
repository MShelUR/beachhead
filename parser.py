# -*- coding: utf-8 -*-
"""
This is a parser for Beachhead command syntax.
"""

import os
import sys
__required_version__ = (3,8)
if sys.version_info < __required_version__:
    print(f"This code will not compile in Python < {__required_version__}")
    sys.exit(os.EX_SOFTWARE)


###
# Credits
###

__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2022, University of Richmond'
__credits__ = None 
__version__ = '0.1'
__maintainer__ = 'George Flanagin'
__email__ = 'gflanagin@richmond.edu'
__status__ = 'Prototype'
__license__ = 'MIT'

###
# Built in imports.
###

import enum
import re

###
# Installed imports.
###
import parsec

###
# hpclib imports
###
from chars import Char
import fileutils
import linuxutils

###
# Regular expressions.
###
COMMENT     = parsec.regex(r'\s*#.*')
IEEE754     = parsec.regex(r'-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?')
PYINT       = parsec.regex(r'[-+]?[0-9]+')
WHITESPACE  = parsec.regex(r'\s*', re.MULTILINE)

# Just what is a keyword? One of these.
KEYWORD = frozenset({'open', 'close', 'socket', 'connection', 'session'})

###
# (lambda) expressions that are a part of the parsing operations.
###


lexeme = lambda p: p << WHITESPACE

lbrace = lexeme(parsec.string(Char.LBRACE.value))
rbrace = lexeme(parsec.string(Char.RBRACE.value))
lbrack = lexeme(parsec.string(Char.LBRACK.value))
rbrack = lexeme(parsec.string(Char.RBRACK.value))
colon  = lexeme(parsec.string(Char.COLON.value))
comma  = lexeme(parsec.string(Char.COMMA.value))

true   = lexeme(parsec.string('true')).result(True) | lexeme(parsec.string('True')).result(True)
false  = lexeme(parsec.string('false')).result(False) | lexeme(parsec.string('False')).result(False)
null   = lexeme(parsec.string('null')).result(None) | lexeme(parsec.string('None')).result(None)

quote  = ( parsec.string(Char.QUOTE1.value) | parsec.string(Char.QUOTE2.value) | parsec.string(Char.QUOTE3.value) )


###
# Functions for parsing more complex elements.
###
def integer() -> int:
    """
    Return a Python int, based on the commonsense def of a integer.
    """
    return lexeme(PYINT).parsecmap(int)


def number() -> float:
    """
    Return a Python float, based on the IEEE754 character representation.
    """
    return lexeme(IEEE754).parsecmap(float)


def charseq() -> str:
    """
    Returns a sequence of characters, resolving any escaped chars.
    """
    def string_part():
        return parsec.regex(r'[^"\\]+')

    def string_esc():
        return parsec.string(BACKSLASH) >> (
            parsec.string(BACKSLASH)
            | parsec.string('/')
            | parsec.string('b').result(Char.BSPACE.value)
            | parsec.string('f').result(Char.VTAB.value)
            | parsec.string('n').result(Char.LF.value)
            | parsec.string('r').result(Char.CR.value)
            | parsec.string('t').result(Char.TAB.value)
            | parsec.regex(r'u[0-9a-fA-F]{4}').parsecmap(lambda s: chr(int(s[1:], 16)))
            | quote
        )
    return string_part() | string_esc()


class EndOfGenerator(StopIteration):
    """
    An exception raised when parsing operations terminate. Iterators raise
    a StopIteration exception when they exhaust the input; this mod gives
    us something useful.
    """
    def __init__(self, value):
        self.value = value

@lexeme
@parsec.generate
def quoted() -> str:
    yield quote
    body = yield parsec.many(charseq())
    yield quote
    raise EndOfGenerator(''.join(body))


@parsec.generate
def array():
    yield lbrack
    elements = yield parsec.sepBy(value, comma)
    yield rbrack
    raise EndOfGenerator(elements)


@parsec.generate
def object_pair():
    key = yield parsec.regex(r'[a-zA-Z][-_a-zA-Z0-9]*') | quoted
    if key in KEYWORD: key = f"{key}_{AX()}"
    yield colon
    val = yield value
    raise EndOfGenerator((key, val))


@parsec.generate
def ijkl_object():
    yield lbrace
    pairs = yield parsec.sepBy(object_pair, comma)
    yield rbrace
    raise EndOfGenerator(dict(pairs))


value = quoted | integer() | number() | ijkl_object | array | true | false | null

ijkl = WHITESPACE >> ijkl_object

class IJKLparser: pass
class IJKLparser:
    """
    A class wrapper for our language.
    """
    def __init__(self, v:bool=False):
        global verbose

        self.data = None
        self.inputfile = None
        self.parsed_data = None

        verbose = v        


    def attachIO(self, f:str) -> IJKLparser:
        """
        Make sure we are parsing a 'real' file.
        """
        self.inputfile = None
        f = fname.Fname(f)
        if f: self.inputfile = str(f)

        return self


    def parse(self) -> linuxutils.SloppyDict:
        """
        Take the input and turn it into a SloppyDict.
        """
        if self.inputfile is None:
            raise Exception("No input attached.")

        self.data = open(self.inputfile).read()
        self._comment_stripper()
        try:
            self.parsed_data = linuxutils.deepsloppy(ijkl.parse(self.data))
            return self.parsed_data

        except Exception as e:
            print(f"Raised {str(e)}")
            return None            
                        

    def dumps(self) -> str:
        """
        Nothing but a wrapper around json.dumps
        """
        global TAB
        return json.dumps(self.parsed_data, indent=TAB)


    def dump(self, f:str) -> bool:
        """
        Rewrite the IJKL as valid JSON.
        """
        global TAB
        f = open(fileutils.expandall(f), 'w')
        json.dump(self.parsed_data, f, indent=TAB) 
        
        

    def _comment_stripper(self) -> None:
        """
        Remove (illegal) bash style comments from the source code.
        Build a list of lines that are really JSON, and join them
        back into a string. 

        A word about the behavior. Bash style comments are printed
        minus the leading octothorpe so that they can be used
        as markers in the compilation process. Blank lines are 
        inserted into the data instead so that the line-numbers
        stay the same, w/ or w/o the comments.
        """
        global LF, EMPTY_STR, OCTOTHORPE, verbose

        if self.data is None: return self

        comment_free_lines = []
        for line in self.data.split(LF):
            if len(line.strip()) == 0: 
                continue

            elif line.strip()[0] == OCTOTHORPE: 
                verbose and print(line[1:])
                continue

            else: 
                comment_free_lines.append(line)

        self.data = LF.join(comment_free_lines)
        return self


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: ijklparser.py file1 [ file2 [ file3 ... ]]")
        sys.exit(os.EX_USAGE)

    p = IJKLparser()
    for f in sys.argv[1:]:
        p.attachIO(f)
        p.parse()
        print(p.dumps())
        p.dump(f+'.new')


