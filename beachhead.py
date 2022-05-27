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

###
# Other standard distro imports
###
import argparse
import cmd
import contextlib
import getpass
import logging

###
# From hpclib
###
import linuxutils
from   urdecorators import show_exceptions_and_frames as trap

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

mynetid = getpass.getuser()


verbosity_levels = {
    1 : logging.CRITICAL,
    2 : logging.ERROR,
    3 : logging.WARNING,
    4 : logging.INFO,
    5 : logging.DEBUG
    }

########################################################

def blue(s:str) -> str:
    return BashColors.BLUE + str(s) + BashColors.REVERT


def red(s:str) -> str:
    return BashColors.YELLOW + str(s) + BashColors.REVERT


def elapsed_time(t1, t2) -> str:
    if t1 > t2: 
        t1, t2 = t2, t1
    e = t2 - t1
    units = ' milliseconds' if e < 1.0 else ' seconds'
    if e < 1.0: e *= 1000
    return str(round(e,3)) + units


indent = "     "
banner = [
    "",
    ' ',
    '='*80,
    indent + ' ',
    indent + '                                                        .-^-.',
    indent + '                                                       \'"\'|`"`',
    indent + '                                                          |',
    indent + ' ',
    indent + '                           /                     '+BashColors.YELLOW + 'BEACHHEAD' + BashColors.REVERT,
    indent + '                /\\________/__/\\ ',
    indent + '   ~~~    ~^~~~~\\________/____/~~~     ooo000000000000000000000000',
    indent + '               ~~~~  ~~ /~          oooooooo0000000oooo00000000000',
    indent + '....................~~^/~........^^o0o0ooo000o000o00o00o00o00o00oo',
    indent + '..<°))))><..                                        o00ooo0ooooo00',
    indent + '............  '+ BashColors.RED + 'From the people who brought you Canøe.' + BashColors.REVERT + '  000o00ooo0o0',
    indent + '.............                                        oo00000oooooo',
    indent + '...................><{{{°>..............................oooxxx0000',
    indent + '',
    indent + BashColors.RED + '  Type `help general` for more information.' + BashColors.REVERT,
    ' ',
    '='*80,
    ""
]

@trap
class Beachhead(cmd.Cmd):
    """
    Beachhead is not a tool for the weak.
    """    

    use_rawinput = True
    doc_header = 'To get a little overall guidance, type `help general`'
    intro = "\n".join(banner)
    prompt = "\n[beachhead]: "
    ruler = '-'

    def __init__(self, myargs:):
        
        cmd.Cmd.__init__(self)
    

    def preloop(self) -> None:
        """
        Get the config (if any). This function updates the self.cfg_file class member
            with the full file name of the one that we will use.
        """

        default_ssh_config_file = '~/.ssh/config'
        f = fname.Fname(default_ssh_config_file)
        if not f:
            logging.warning('You do not seem to have an ssh config file. This program')
            logging.warning('may not be very useful.')


    def default(self, line):
        """
        This program does not use the "do_*" functions directly. Instead,
        this function uses parsec to read the tokens in accordance with the
        beachhead grammar.
        """
        tokens = beachhead_parser(line)


@trap
def beachhead_main(myargs:argparse.Namespace) -> int:
    """
    
    """
    logging.basicConfig(filename=myargs.output, 
        encoding='utf-8',
        filemode='a',
        level = verbosity_levels[myargs.verbose])    
    beachhead_shell = Beachhead()

    try:
        beachhead_shell.cmdloop()
    except KeyboardInterrupt as e:
        print("You pressed control-C. Exiting.")
        return os.EX_OK
    except Exception as e:
        pass

    return os.EX_OK


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog="beachhead", 
        description="What beachhead does, beachhead does best.")

    parser.add_argument('-o', '--output', type=str, default="beachhead.log",
        help="Name of file to contain the results.")

    parser.add_argument('-v', '--verbose', type=int, default=1, choices=range(1, 6),
        help="Be chatty about what is taking place (in the log file)")

    myargs = parser.parse_args()
    myargs.verbose and linuxutils.dump_cmdline(myargs)
    if myargs.nice: os.nice(myargs.nice)

    try:
        sys.exit(globals()[f"{os.path.basename(__file__)[:-3]}_main"](myargs))

    except Exception as e:
        print(f"Escaped or re-raised exception: {e}")


