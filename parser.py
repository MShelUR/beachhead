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

class EndOfGenerator(StopIteration):
    """
    An exception raised when parsing operations terminate. Iterators raise
    a StopIteration exception when they exhaust the input; this mod gives
    us something useful.
    """
    def __init__(self, value):
        self.value = value

###
# Regular expressions.
###
# Comment is a line in which the # is the first non-whitespace character.
COMMENT_LINE = re.compile(r'^\s*#.*$')
EOL_COMMENT = parsec.regex(r'\s*#.*$')

# Floating point number
IEEE754 = parsec.regex(r'-?(0|[1-9][0-9]*)([.][0-9]+)?([eE][+-]?[0-9]+)?')
# Integer
PYINT = parsec.regex(r'[-+]?[0-9]+')
# Allow for multiline gaps
WHITESPACE = parsec.regex(r'\s*', re.MULTILINE)

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
equal  = lexeme(parsec.string(Char.EQUAL.value))
dash   = lexeme(parsec.string(Char.DASH.value))

true   = (  lexeme(parsec.string('true')).result(True) | 
            lexeme(parsec.string('True')).result(True) )
false  = (  lexeme(parsec.string('false')).result(False) | 
            lexeme(parsec.string('False')).result(False) )
null   = (  lexeme(parsec.string('null')).result(None) | 
            lexeme(parsec.string('None')).result(None) )

quote  = (  parsec.string(Char.QUOTE1.value) | 
            parsec.string(Char.QUOTE2.value) | 
            parsec.string(Char.QUOTE3.value) )


command_text = frozenset(('open', 'close', 'send', 'get'))
noun_text = frozenset(('socket', 'connection', 'file'))

command = tuple(lexeme(parsec.string(x)).result(x) for x in command_text)
noun = tuple(lexeme(parsec.string(x)).result(x) for x in noun_text)

###
# Functions for parsing more complex elements. These are standard across
# most computer languages.
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
            | parsec.string('"').result(Char.QUOTE2.value)
            | parsec.string("'").result(Char.QUOTE1.value)
            | parsec.regex(r'u[0-9a-fA-F]{4}').parsecmap(lambda s: chr(int(s[1:], 16)))
            | quote
        )
    return string_part() | string_esc()


def eol_comment() -> str:
    yield EOL_COMMENT
    raise EndOfGenerator(EMPTY_STR)


@lexeme
@parsec.generate
def quoted() -> str:
    """
    If a string is in quotes, we do not try to parse within the quotes.
    Collect everything and return it.
    """
    open_mark = yield quote
    body = yield parsec.many(charseq())
    close_mark = yield quote
    if open_mark != close_mark:
        raise Exception(f"Mismatched quotes around {body}")
    else:
        raise EndOfGenerator(''.join(body))


@parsec.generate
def array() -> list:
    """
    Handle a list of comma separated tokens, enclosed by [ ]
    """
    yield lbrack
    elements = yield parsec.sepBy(value, comma)
    yield rbrack
    raise EndOfGenerator(elements)


@parsec.generate
def alnum() -> str:
    """
    An alphanumeric token that starts with a letter.
    """
    token = yield parsec.regex(r'[a-zA-Z][-_a-zA-Z0-9]*')
    raise EndOfGenerator(token)


@parsec.generate
def option() -> str:
    """
    A double dash option.
    """
    yield dash
    yield dash
    yield alnum
    yield value
    raise EndOfGenerator(alnum, value)    


@parsec.generate
def kv_pair():
    """
    Handle an alphanumeric token, followed by =, followed by a value.
    """
    key = yield parsec.regex(r'[a-zA-Z][-_a-zA-Z0-9]*') 
    yield equal
    val = yield value
    raise EndOfGenerator((key, val))


value = quoted | integer() | number() | array | kv_pair | alnum | true | false | null
complete_command = WHITESPACE >> eol_comment() | command | noun | option | value


class BeachheadParser: pass
class BeachheadParser:
    """
    A class wrapper for commands.
    """
    def __init__(self, v:bool=False):
        self.data = None
        self.parsed_data = None


    def attachIO(self, s:str) -> BeachheadParser:
        """
        The input is a line of text.
        """
        self.input_data = str(s)
        return self


    def parse(self) -> linuxutils.SloppyDict:
        """
        Take the input and turn it into a SloppyDict.
        """
        if self.input_data is None:
            raise Exception("No data to read.")

        self._comment_stripper()
        try:
            self.parsed_data = linuxutils.deepsloppy(
                complete_command.parse(self.input_data)
                )
            return self.parsed_data

        except Exception as e:
            print(f"Raised {str(e)}")
            return None            

        finally:
            self.input_data = None
                        

    def _comment_stripper(self) -> None:
        """
        Remove bash style comments from the source code.
        Build a list of lines that are really JSON, and join them
        back into a string. 

        A word about the behavior. Bash style comments are printed
        minus the leading octothorpe so that they can be used
        as markers in the compilation process. Blank lines are 
        inserted into the data instead so that the line-numbers
        stay the same, w/ or w/o the comments.
        """
        if not self.data or re.fullmatch(COMMENT_LINE, self.data): 
            self.input_data = ""

        return


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


