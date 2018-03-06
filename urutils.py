# -*- coding: utf-8 -*-
""" Generic, bare functions, not a part of any object or service. """

# Added for Python 3.5+
import typing
from typing import *

import argparse
import atexit
import base64
import binascii
import calendar
import collections
import croniter
import datetime
import dateutil
from   dateutil import parser
import functools
from   functools import reduce
import getpass
import inspect
import io
import json
import operator
import os
import paramiko
import pprint as pp
import psutil
import random
import re
import shlex
import shutil
import signal
import socket
import stat
import string
import sortedcontainers
import subprocess
import sys
import tempfile
import time
import traceback

# Credits
__longname__ = "University of Richmond"
__acronym__ = " UR "
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2015, University of Richmond'
__credits__ = None
__version__ = '0.1'
__maintainer__ = 'George Flanagin'
__email__ = 'gflanagin@richmond.edu'
__status__ = 'Prototype'

LIGHT_BLUE="\033[1;34m"
BLUE = '\033[94m'
RED = '\033[91m'
YELLOW = '\033[1;33m'
REVERSE = "\033[7m"
REVERT = "\033[0m"


pig = [
    "                         _",
    " _._ _..._ .-',     _.._(`))",
    "'-. `     '  /-._.-'    ',/",
    "   ) " + __acronym__ + "    \            '.",
    "  / -    -    | The Safety  \\",
    " |  O    O    /  Pig         |",
    " \   .-.                     ;  ",
    "  '-('' ).-'       ,'       ;",
    "     '-;           |      .'",
    "        \           \    /",
    "        | 7  .__  _.-\   \\",
    "        | |  |  ``/  /`  /",
    "       /,_|  |   /,_/   /",
    "          /,_/      '`-'",
    " "]

# Cheap hack so that "*" means "every{minute|hour|etc}"
class Universal(set):
    """
    Universal set - match everything. No matter the value
    of item, s.o.b., Mr. Wizard, it's there!
    """
    def __contains__(self, item): return True


# And an instance.
star = Universal() 


# Cheap hack to get sequence numbers for tombstones.

class Accumulator(object):
    """
    This only works in a multi-processing environment because
    we care about the monotonic increasing property of the 
    numbers, not their values or whether the set of values is
    duplicated in a forked process.

    Syntax:

        i = Sequence()
    """
    ax = 0

    def __init__(self):
        pass

    def __call__(self):
        Accumulator.ax += 1
        return Accumulator.ax

    def __int__(self):
        return ax

# And here is the accumulator itself.
AX=Accumulator()

####
# A
####

def all_ASCII(s: str) -> bool:
    """ 
    Ensure ASCII-ness.
    s -- a string.

    returns: -- True only if all characters in the string are ASCII.
        Empty strings are construed to be all ASCII, as they do not
        change the ASCII-ness of another string when concatenated.
    """
    if not len(s): return True
    return reduce(operator.mul, [int(ascii(x)) and int(ascii(x)) < 128 for x in list(s)], 1) == 1


def asciify(s: str) -> str:
    """ Convert chars in string to ascii-only by 'flattening'

    s - string to be transformed.
    returns: - a possibly empty transformation of s.
    """
    return str(s).encode('ascii', 'ignore')



def ask(obj:Any, host:str, port:int, EOM:str="$$$") -> str:
    """ This function is used to transmit JSON over a socket.

    obj -- a snippet of data, generally a true object, that needs
        to be rewritten as a JSON string.
    host -- the name of some machine on the interwebs.
    port -- the host's listen port.
    EOM -- a software marking indicating the end-of-message.

    returns: -- The reply as a string without EOM on the end, 
        or None on error.
    """

    reply = ""
    buf = ""
    if not isinstance(obj, str): obj = json.dumps(obj) + str(EOM)
    if not obj: return None

    try:
        the_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        the_sock.setblocking(1)
        the_sock.connect((socket.gethostbyname(host), port))
        the_sock.sendall(bytes(obj, 'utf-8'))
    except socket.error:
        print ('socket error ' + socket.error)
        return None
    while True:
        try:
            buf = the_sock.recv(4096)
        except socket.error: 
            pass
        except KeyboardInterrupt:
            tombstone("Aborting request. crtl-C detected on keyboard.")
            return
        finally:
            reply = reply + buf
        if len(buf) < 4096 or reply.endswith(EOM): break

    if reply.endswith(EOM): reply = reply[:-3]

    return reply


####
# B
####

def bad_exit() -> None:
    tombstone("Halted by signal at " + time.ctime())
    fclose_all()
    os._exit(0)    


def blind(s:str) -> str:
    """
    Produce /blinding/ reverse video around the display of a string.
    """
    global REVERSE
    global REVERT
    return " " + REVERSE + s + REVERT + " " 


####
# C
####

def canoe_schedule(s:str) -> List[List[Set]]:
    """
    Deal with special cases...

    @adhoc -- create a schedule that never matches any date.
    @canoe=file-name-with-schedules-one-per-line
    @random=stuff. See explanation in the code below.

    returns what it finds.
    """
    never = [ {61}, {25}, {32}, {13}, {8} ]
    items = []

    if s.startswith('@canoe='):
        lhs, rhs = s.split('=')
        with open(os.path.expandvars(os.path.expanduser(rhs.strip())), 'r') as f:
            schedules = f.read().split("\n")

        for _ in schedules:
            try:
                t = dateutil.parser.parse(_).timetuple()[1:5]
                s = " ".join([str(e) for e in t[::-1]]) + " *"
                items.append(parse_schedule(s))
            except ValueError as e:
                items.append(parse_schedule(_))

    elif s.startswith('@random='):
        """
        This is a regular schedule in every way except one,
        namely that the minute term is written as 
        [0-9][0-9]?[xX]. This term tells how many times
        per hour you wish to run. 
        """
        terms = s[8:].strip().split()
        try:
            tries = int(terms[0][:-1])
        except:
            tries = 0
            tombstone('ignoring invalid schedule ' + s)
        terms[0] = "0"
        schedule = parse_schedule(" ".join(terms))
        schedule[0] = set([ 
            random.randrange(60) for i in range(0, tries) 
            ])
        return schedule    

    elif s == '@adhoc': 
        return never

    else:
        raise Exception('Unknown schedule: ' + str(s))

    return [ item for item in items if item ]


def cron_to_str(cron:Tuple[Set]) -> Dict:
    """
    Return an English explanation of a crontab entry.
    """

    if len(cron) != 5: return "This does not appear to be a cron schedule"
    
    keynames=["a_minutes","b_hours","c_days","d_months","e_dows"]
    explanation = dict.fromkeys(keynames)

    for time_unit, sched in zip(keynames, cron):

        # This is self explanatory, right?
        if sched == star:
            explanation[time_unit] = 'all ' + time_unit[2:]
            continue
        
        # Test for the exact value (often the case for min, hr, dow)
        valid = sorted(list(sched))
        if len(valid) == 1:
            explanation[time_unit] = time_unit[2:] + " " + str(valid[0])
            continue

        if valid == list(range(valid[0], valid[-1]+1)):
            explanation[time_unit] = (time_unit[2:] + " " + str(valid[0]) + 
                " to " + str(valid[-1]))
            continue

        # Test for every fifth minute, third month, etc. Maybe some 
        # explanation is required ... zip() stops when the first target
        # of the pair is empty. We subtract the neighbors (remember, it
        # already sorted), and make a set. If the set only has one
        # element, then the neighbors are equally spaced apart.

        diffs = set([ j - i for i, j in zip(valid, valid[1:]) ])
        if len(diffs) == 1:
            explanation[time_unit] = (time_unit[2:] + 
                " every " + str(diffs.pop()) + 
                " from " + str(valid[0]) + " to " + str(valid[-1]))
            continue

        # TODO: tune this up a bit.

        explanation[time_unit] = time_unit[2:] + " in " + str(valid)

    return explanation


def crontuple_now():
    """
    Return /now/ as a cron-style tuple.
    """
    return datetime.datetime(*datetime.datetime.now().timetuple()[:6])


####
# D
####

def date_filter(filename:str, *, 
    year:str="YYYY", 
    year_contracted:str="Y?",
    month:str="MM", 
    month_contracted:str="M?",
    month_name:str="bbb",
    week_number:str="WW",
    day:str="DD",
    day_contracted:str="D?",
    hour:str="hh",
    minute:str="mm",
    second:str="ss",
    date_offset:int=0) -> str:
    """
    Remove placeholders from a filename and use today's date (with
    an optional offset).

    NOTE: all the placeholders are non-numeric, and all the replacements 
        are digits. Thus the function works because the two are disjoint
        sets. Break that .. and the function doesn't work.
    """
    if not isinstance(filename, str): return filename

    #Return unmodified file name if there isn't at least one set of format delimiters "{" and "}"
    if not re.match(".*?\{.*?\}.*?", filename):
        return filename

    today = crontuple_now() + datetime.timedelta(days=date_offset)

    # And now ... for Petrarch's Sonnet 47
    this_year = str(today.year)
    this_year_contracted = this_year[2:]
    this_month_name = calendar.month_abbr[today.month].upper()
    this_month = str('%02d' % today.month)
    this_month_contracted = this_month if this_month[0] == '1' else this_month[1]
    this_week = str('%02d' % datetime.date.today().isocalendar()[1])
    this_day =  str('%02d' % today.day)
    this_day_contracted = this_day if this_day[0] != '0' else this_day[1]
    this_hour = str('%02d' % today.hour)
    this_minute = str('%02d' % today.minute)
    this_second = str('%02d' % today.second)

    #Initialize new_filename so we can use it later
    new_filename = filename
    
    #Iterate through each pair of "{" and "}" in filename and replace placeholder values
    #with date literals
    for date_exp in [ m.group(0) for m in re.finditer("\{.*?\}",filename) ]:
        #Start with the sliced substring excluding the "{" and "}" charactes and
        #begin replacing pattern date strings with literals
        new_name = date_exp[1:-1].replace(year, this_year)
        new_name = new_name.replace(year_contracted, this_year_contracted)
        new_name = new_name.replace(month_name, this_month_name)
        new_name = new_name.replace(month, this_month)
        new_name = new_name.replace(month_contracted, this_month_contracted)
        new_name = new_name.replace(week_number, this_week)
        new_name = new_name.replace(day, this_day)
        new_name = new_name.replace(day_contracted, this_day_contracted)
        new_name = new_name.replace(hour, this_hour)
        new_name = new_name.replace(minute, this_minute)
        new_name = new_name.replace(second, this_second)
        #Now replace the original string including the "{" and "}" with the translated string
        new_filename = new_filename.replace(date_exp,new_name)

    #Return result and strip { and } format containers
    return new_filename


def datetime_encoder(obj:Any) -> str:
    """
    If Oracle DATETIME objects come back to the program via cx_Oracle,
    they are a non-serializable type. This class is a hook that 
    spots them, and returns the YYYY-MM-DD part of the ISO 8601 
    formatted string.

    If the argument is /not/ a DATETIME type, then we pass it along
    to the bog standard encoder.
    """
    try:
        return obj.isoformat()[:10]
    except:
        return json.JSONEncoder.default(self, obj)


def dictify(args:str) -> Dict[str, str]:
    """
    We take commonsense narratives like:

       " subject= report88, sender =system@starrez.com"

    and change them into implicit Python keyword arguments
    that resemble this tidy collection of keys and values.

        {"subject":"report88", "sender":"system@starrez.com"}
    """
    the_dict = collections.defaultdict(lambda:"")

    args = args.strip().split(',')
    for arg in args:
        try:
            x, y = arg.strip().split('=')
            the_dict[x.strip()] = y.strip()
        except:
            the_dict[arg.strip()]

    return the_dict
            

def dict_walk(d:Dict[Hashable, Any]) -> Dict[Hashable, Any]:
    """
    Blow down the keys and values of a nested data structure.
    """
    for k, v in d.items():
        if type(v) is dict:
            yield from dict_walk(v)
        else:
            yield (k, v)

def do_not_run_twice(name:str) -> None:
    """
    Prevents multiple executions at startup. Note that you shouldn't
    call this function from a program after it may have forked into
    multiple processes.
    """
    pids = pids_of(name, True)
    if len(pids):
        tombstone(name + " appears to be already running, and has these PIDs: " + str(pids))
        sys.exit(os.EX_OSERR)


def dump_cmdline(args:argparse.ArgumentParser, return_it:bool=False) -> str:
    """
    Print the command line arguments as they would have been if the user
    had specified every possible one (including optionals and defaults).
    """
    if not return_it: print("")
    opt_string = ""
    for _ in sorted(vars(args).items()):
        opt_string += " --"+ _[0].replace("_","-") + " " + str(_[1])
    if not return_it: print(opt_string + "\n")
    
    return opt_string if return_it else ""


def dump_exception(e:Exception, line:int=0, fcn:str=None, module:str=None) -> str:
    """ Tell us what we really [don't] want to know. """
    cf = inspect.stack()[1]
    f = cf[0]
    i = inspect.getframeinfo(f)

    line = str(i.lineno) if line == 0 else line
    module = i.filename if not module else module
    junk, exception_type = str(type(e)).split()
    exception_type = exception_type.strip("'>")

    msg = []
    msg.append("Caught @ line " + line + " in module " + module + 
            ".\n" + str(e) + " :: raised by " + exception_type)
    # squeal(msg)k
    msg.extend(formatted_stack_trace())
    return "\n".join(msg)


####
# E
####

def empty(o:Any) -> bool:
    """
    Roughly equivalent to PHP's empty(), but goes farther. Oddly formed
    JSON constructions like {{}} and {[]} need to be considered empty.
    """

    # See if it is "False" by the usual means. 
    if not o: return True

    # Determine if it might be a collection of Falsies.
    try:
        r = functools.reduce(operator.and_, [empty(oo) for oo in o])
    except:
        return False
    
    return r


def empty_to_null_literal(s:str) -> str:
    """ For creating database statements with a literal NULL

    s -- string to assess
    returns: -- s or 'NULL'

    >>> empty_to_null_literal('')    
    'NULL'
    >>> empty_to_null_literal('NULL')
    'NULL'
    >>> empty_to_null_literal(5)
    '5'
    >>> empty_to_null_literal('george')
    'george'
    """

    return (str(s) if (not isinstance(s, str) or len(s) > 0) else 'NULL')


####
# F
####

def fclose_all() -> None:
    for i in range (0, 1024):
        try:
            os.close(i)
        except:
            continue


def fcn_signature(*args) -> str:
    """
    provide a string for debugging that resembles a function's actual
    arguments; i.e., how it was called. The zero-th element of args 
    should be the name of the function, and then the arguments follow.
    """
    if not args: return "()"

    s = args[0] + "("
    s += ", ".join([str(_) for _ in args[1:]])
    s += ")"
    return s


def fcopy_safe(file1:str, file2:str, 
        mode:int=stat.S_IRUSR|stat.S_IWUSR|stat.S_IRGRP,
        num_attempts:int=2) -> int:
    """
    Carefully copy from something that looks like a file to another file,
    ensuring that the contents are really there.

    file1 -- file object associated with an open file.

    file2 -- either a filename (str) or something we have open-ed from
        elsewhere in the Python program.

    returns -- one of the os.EX_* entries. Returns os.EX_OK if and only if
        the destination file was successfully closed or the error is 
        trivial.
    """
    fd1 = fd2 = None

    if os.path.realpath(file1) == os.path.realpath(file2):
        tombstone("{} and {} are the same pathname.".format(file1, file2))
        return os.EX_OK

    if not os.stat(file1).st_size:
        tombstone("stubbornly refusing to copy empty file {}".format(file1, file2))
        return os.EX_OK

    try:
        fd1 = open(file1, 'rb')
    except OSError as e:
        tombstone(type_and_text(e))
        return os.EX_DATAERR

    try:
        fd2 = open(file2, 'wb')

    except FileNotFoundError as e:
        tombstone(type_and_text(e))
        tombstone('ACHTUNG! Checking to see if directories exist for {}'.format(file2))
        pieces = file2.split(os.sep)[1:-1]
        tombstone(str(pieces))
        top = os.sep
        for piece in pieces:
            top = (os.sep).join([top, piece])
            if os.path.isdir(top): 
                tombstone("Checking ... {}".format(top))
                continue
            else: 
                tombstone('Problem is with {}.'.format(top))   
                return os.EX_CANTCREAT
        else:
            tombstone('Likely problems with relative directory names.')
            return os.EX_CANTCREAT
        
    except Exception as e:
        tombstone(type_and_text(e))
        return os.EX_CANTCREAT

    """ At long last we have fd1 and fd2. """
    try:
        shutil.copyfileobj(fd1, fd2) 
    except Exception as e:
        tombstone(type_and_text(e))
        return os.EX_IOERR

    try:
        os.chmod(file2, mode)
    except Exception as e:
        tombstone(type_and_text(e))
        return os.EX_CONFIG

    for _ in range(0, num_attempts):
        try:
            os.stat(file2)
        except Exception as e:
            tombstone(type_and_text(e))
        else:
            return os.EX_OK
    else:
        return os.EX_UNAVAILABLE


def formatted_stack_trace(as_string: bool = False) -> str:
    """ Easy to read, tabular output. """

    exc_type, exc_value, exc_traceback = sys.exc_info()
    this_trace = traceback.extract_tb(exc_traceback)
    r = []
    r.append("Stack trace" + "\n" + "-"*80)
    for _ in this_trace:
        r.append(", line ".join([str(_[0]), str(_[1])]) +
            ", fcn <" + str(_[2]) + ">, context=>> " + str(_[3]))
    r.append("="*30 + " End of Stack Trace " + "="*30)
    return "\n".join(r) if as_string else r


def fcn_signature(*args) -> str:
    """
    provide a string for debugging that resembles a function's actual
    arguments; i.e., how it was called. The zero-th element of args 
    should be the name of the function, and then the arguments follow.
    """
    if not args: return "()"

    s = args[0] + "("
    s += ", ".join([str(_) for _ in args[1:]])
    s += ")"
    return s


####
# G
####

def get_ssh_host_info(host_name:str=None, config_file:str=None) -> List[Dict]:
    """ Utility function to get all the ssh config info, or just that
    for one host.

    host_name -- if given, it should be something that matches an entry
        in the ssh config file that gets parsed.
    config_file -- if given (as it usually is not) the usual default
        config file is used.
    """

    if config_file is None:
        config_file = os.path.expanduser("~") + "/.ssh/config"

    try:
        ssh_conf = paramiko.SSHConfig()
        ssh_conf.parse(open(config_file))
    except:
        raise Exception("could not understand ssh config file", this_line())

    if not host_name: return ssh_conf
    if host_name == 'all': return ssh_conf.get_hostnames()
    return None if host_name not in ssh_conf.get_hostnames() else ssh_conf.lookup(host_name)


def got_data(filenames:str) -> bool:
    """
    Return True if the file or files all are non-empty, False otherwise.
    """
    if filenames is None or not len(filenames): return False

    filenames = listify(filenames)
    result = True
    for _ in filenames:
        result = result and bool(os.path.isfile(_)) and bool(os.stat(_).st_size)
    return result

####
# H
####

def hexify(msg_id:bytes) -> str:
    return binascii.hexlify(msg_id)


####
# I
####

def in_production(g:Dict) -> bool:
    """ 
    This function should be used to determine if the caller is a part of a 
    process that is running in the environment we designate as PRODUCTION.
    The rules for running in production are tighter, and how this is determined
    may change in the future. Therefore, do not make a simple hard-coded
    comparison of values.
    """
    return g.env['this_env'] == 'PROD'


def is_phone_number(s:str) -> bool:
    """ Determines if s could be a USA phone number. """

    return len(s) == 10 and s.isdigit()


def iso_time(seconds:int) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(seconds))


def iso_seconds(timestring:str) -> int:
    try:
        dt = datetime.datetime.strptime(timestring, '%Y-%m-%dT%H:%M')
    except:
        raise URException("Malformed time: " + timestring)
    else:
        return dt.strftime("%s")


####
# L
####

def lines_in_file(filename:str) -> int:
    """
    Count the number of lines in a file by a consistent means.
    """
    if not os.path.isfile(filename): return 0

    try:
        count = int(subprocess.check_output([
            "/bin/grep", "-c", os.linesep, filename
            ], universal_newlines=True).strip())
    except subprocess.CalledProcessError as e:
        tombstone(str(e))
        return 0
    except ValueError as e:
        tombstone(str(e))
        return -2
    else:
        return count
    

def listify(x:object) -> List[object]:
    """ 
    change a single element into a list containing that element, but
    otherwise just leave it alone. 
    """
    try:
        if not x: return[]
    except NameError as e:
        return []
    return x if isinstance(x, list) else [x]


####
# M
####

def make_dir_or_die(dirname:str, mode:int=0o700) -> None:
    """
    Do our best to make the given directory (and any required 
    directories upstream). If we cannot, then die trying.
    """

    try:
        os.makedirs(dirname, mode)

    except FileExistsError as e:
        # It's already there.
        pass

    except PermissionError as e:
        # This is bad.
        tombstone()
        tombstone("Permissions error creating/using " + dirname)
        exit(1)

    except NotADirectoryError as e:
        tombstone()
        tombstone(dirname + " exists, but it is not a directory")
        exit(1)

    except Exception as e:
        tombstone()
        tombstone(type_and_text(e))
        exit(1)
        # This means the directory already exists.

    if (os.stat(dirname).st_mode & 0o777) >= mode:
        return
    else:
        tombstone()
        tombstone("Permissions on " + dirname + " less than requested.")


def make_IN_clause(a:Union[List,str]) -> str:
    """ Changes the argument, often a list, into an 'IN (e, e, e)' clause

    a -- a value, or a list of more than one value. The type of a is
        irrelevant.
    returns: -- An SQL fragment suitable for inclusion in an SQL statement.

    >>> make_IN_clause('george')
    " IN ('george') "

    >>> make_IN_clause(['george', 'flanagin'])
    " IN ('george','flanagin') "
    """

    if not isinstance(a, list): a = [a]
    return " IN (" + (",".join([q(_) for _ in a])) + ") "


def me() -> str:
    return getpass.getuser()


def mdays(urcal:dict) -> sortedcontainers.SortedList:
    """
    The urcal is a dict with two lists attached to the keys bizdays and 
    holidays. We need to build up a sorted list of the non-holiday bizdays
    involved.
    """
    start = urdate()
    urcal['holidays'] = [ urdate(dateutil.parser.parse(_)) for _ in urcal['holidays']]

    """
    Let's start ten days before now, and go a year and change out
    into the future. We have to start a little before today to take care 
    of the recipes that might be starting now, and have a date modification
    that takes them to yesterday, or last Friday, etc.
    """
    return sortedcontainers.SortedList([ _ for _ in range(start-10, start+400) 
        if _ % 7 in urcal['bizdays']
        and _ not in urcal['holidays']])


####
# N
####

def normalize_phone_number(s: str) -> str:
    """ Remove the non-digits from the string. """
    t = []
    for c in s:
        if c in list(string.digits): t.append(c)
    return ''.join(t)


def now_as_seconds() -> int:
    return time.clock_gettime(0)


def now_as_string() -> str:
    """ Return full timestamp for printing. """
    return datetime.datetime.now().isoformat()[:21].replace('T',' ')


####
# P
####

def parse_proc(pid:int) -> dict:
    """
    Parse the proc file for a given PID and return the values
    as a dict with keys set to lower without the "vm" in front,
    and the values converted to ints.
    """
    lines = []
    proc_file = '/proc/'+str(pid)+"/status"
    with open(proc_file, 'r') as f:
        rows = f.read().split("\n")

    if not len(rows): return None

    interesting_keys = ['VmSize', 'VmLck', 'VmHWM', 
            'VmRSS', 'VmData', 'VmStk', 'VmExe', 'VmSwap' ]

    kv = {}
    for row in rows:
        if ":" in row:
            k, v = row.split(":")
        else:
            continue
        if k in interesting_keys: 
            try:
                kv[k.lower()[2:]] = int(v.split()[0])
            except Exception as e:
                tombstone(type_and_text(e))

    return kv


def parse_schedule(s:str) -> List[Set]:
    """
    Changes a crontab type schedule descriptor into a list of sets,
    where each set contains the matching values for each schedule
    element.

    Big change on 16 March 2017. We now handle @canoe directives.
    """
    s = s.strip()
    if not s: return []

    try:
        cron_parser = croniter.croniter(s)
        return [ setify(_) for _ in cron_parser.expanded ]
    except Exception as e:
        return canoe_schedule(s)


def parse_schedules(scheds:List[str]) -> List[List[Set]]:
    """
    Iteratively call parse_schedule, and return a list of
    lists of sets.  i.e., 
    
        [
            [ {0}, {0}, {1}, {1}, {1} ],
            [ {0,30}, ... ]
        ]
    """
    parsed = []
    if not scheds: return parsed

    for sched in listify(scheds): 
        result = parse_schedule(sched)
        if all(isinstance(_, set) for _ in result):
            parsed.append(result)
        else:
            parsed.extend([ _ for _ in result if _ ])
        
    return parsed


def parse_user_input(s:str, transformation:int=0) -> Tuple[List[str], bool]:
    """
    Do a whitespace parse on the input, and return whether there was
    anything other than one string.

    s -- a string, presumably typed in by the user.
    transformation -- a bit mask, prescribing appropriate changes
        1 -> to lower case
        2 -> to ASCII
    
    returns -- tuple(list, bool) 
                The list is a (possibly empty) collection of tokens,
                _nand the bool has these meanings:
                True -- there was exactly one token
                False -- there was more than one token
                None -- there was nothing, or an empty string.
    """
    tokens = []
    nothing_worth_doing = None
    try:
        if s is None: return tokens, nothing_worth_doing
        s = s.strip()
        if not len(s): return tokens, nothing_worth_doing
        s = s.lower() if transformation & 1 else s
        s = s.decode('utf-8').encode('ascii') if transformation & 2 else s
        if not s: tokens, nothing_worth_doing

        tokens = shlex.split(s)
        nothing_worth_doing = len(tokens) == 1 and tokens[0] == s
    except Exception as e:
        tombstone(type_and_text(e))
    finally:
        return tokens, nothing_worth_doing


def parse_JSON_file(filename: str):
    """ strip bash style comments from an otherwise JSON file. """
    json_string = []
    for line in open(filename, 'r').readlines().strip():
        if not line or line[0] == '#': continue
        json_string.append(line)

    return json.loads(''.join(json_string))


def pids_of(process_name:str, anywhere:bool = False) -> list:
    """
    Canøe is likely to have more than one background process running, 
    and we will only know the first bit of the name, i.e., "canoed".
    This function gets a list of matching process IDs.

    process_name -- a text shred containing the bit you want 
        to find.
    anywhere -- If False, we effectively look for a partial name.

    returns -- a possibly empty list of ints containing the pids 
        whose names match the text shred.
    """
    results = []
    search = ['name']

    for p in psutil.process_iter(attrs=search):

        if process_name == p.info['name']:
            results.append(p.pid)
        elif anywhere and process_name in p.info['name']:
            results.append(p.pid)

    return results


###
# Q
###

def q(ins:str, quoteType:int=1) -> str:
    """A general purpose string quoter and Houdini (mainly for SQL)

    ins -- an input string
    quote_type -- an integer between 0 and 5. Meanings:
        0 : do nothing
        1 : ordinary single quotes.
        2 : ordinary double quotes.
        3 : Linux/UNIX backquotes.
        4 : PowerShell escape and quoting.
        5 : SQL99 escaping only.
    returns: -- some version of 's'.
    """

    quote = "'"
    if quoteType == 1:
        return quote + ins.replace("'", "''") + quote
    elif quoteType == 2:
        quote = '"'
        return quote + ins.replace('"', '\\"') + quote
    elif quoteType == 3:
        quote = '`'
        return quote + ins + quote
    elif quoteType == 4: # Powershell
        ins = re.sub('^', '^^', ins)
        ins = re.sub('&', '^&', ins)
        ins = re.sub('>', '^>', ins)
        ins = re.sub('<', '^<', ins)
        ins = re.sub('|', '^|', ins)
        ins = re.sub("'", "''", ins)
        return quote + ins + quote
    elif quoteType == 5: # SQL 99 .. quotes only.
        return quote + re.sub("'",  "''", ins) + quote
    else:
        pass
    return ins


def q64(s:str, quote_type:int=1) -> bytes:
    """ Convert to Base64 before quoting.

    s -- a string to convert to Base64.
    returns: -- same thing as q()
    """
    return b"'" + encodebytes(s.encode('utf-8')) + b"'"


def q_like(s:str) -> str:
    """ Prepend and append a %

    s -- a string
    returns: -- %s%
    """
    return q("%" + s + "%")


def q_like_pre(s:str) -> str:
    """ append a %

    s -- a string
    returns: -- s%
    """

    return q("%" + s)


def q_like_post(s:str) -> str:
    """ Append a %

    s -- a string
    returns: -- s%
    """

    return q(s + "%")

###
# O
###
def oracle_type_to_python(oracle_type:str, precision:int) -> str:
    """
    Convert an Oracle 10+ type name into something Pythonic.
    """
    if oracle_type[:3] in ['NUM']: 
        return 'int' if precision == 0 else 'float'
    if oracle_type[:3] in ['BIN']: return 'float'
    if oracle_type[:3] in ['DAT', 'TIM', 'INT']: return 'datetime'
    if oracle_type[:3] in ['CHA', 'NCH', 'NVA', 'VAR', 'LON', 'RAW']: return 'str'
    if oracle_type[:3] in ['ROW']: return 'str'
    return 'object'


####
# R
####

def random_file(name_prefix:str, *, length:int=None, break_on:str=None) -> tuple:
    """
    Generate a new file, with random contents, consisting of printable
    characters.

    name_prefix -- In case you want to isolate them later.
    length -- if None, then a random length <= 1MB
    break_on -- For some testing, perhaps you want a file of "lines."

    returns -- a tuple of file_name and size.
    """    
    f_name = None
    num_written = -1

    file_size = length if length is not None else random.choice(range(0, 1<<20))
    fcn_signature('random_string', file_size)
    s = random_string(file_size, True)

    if break_on is not None:
        if isinstance(break_on, str): break_on = break_on.encode('utf-8')
        s = s.replace(break_on, b'\n')    

    try:
        f_no, f_name = tempfile.mkstemp(suffix='.txt', prefix=name_prefix)
        num_written = os.write(f_no, s)
        os.close(f_no)
    except Exception as e:
        tombstone(str(e))
    
    return f_name, num_written
    


def random_string(length:int=10, want_bytes:bool=False, all_alpha:bool=True) -> str:
    """
    
    """
    
    s = base64.b64encode(os.urandom(length*2))
    if want_bytes: return s[:length]

    s = s.decode('utf-8')
    if not all_alpha: return s[:length]

    t = "".join([ _ for _ in s if _.isalpha() ])[:length]


def remove_empty_items(x:list) -> list:
    """ 
    Remove any empty strings and None-s, but not the zero 
    or False values. 
    """
    return list(filter(len, remove_none_items(x)))


def remove_none_items(x:list) -> list:
    """ Scrub None items only. """
    return list(filter(None.__ne__, x))


####
# S
####

def schedule_match(t1:tuple, t2:tuple) -> bool:
    return ((t1.tm_min in t2[0]) and
            (t1.tm_hour in t2[1]) and
            (t1.tm_mday in t2[2]) and
            (t1.tm_mon in t2[3]) and
            (((t1.tm_wday+1) % 7) in t2[4]))


def setify(obj):
    """
    If it is not a set going in, it will be coming out.
    """
    global star
    if str(obj) == '*':
        return star
    if isinstance(obj, int):
        return set([obj])  # Single item
    if isinstance(obj, list) and obj[0] == '*':
        return star
    if not isinstance(obj, set):
        obj = set(obj)
    return obj


def squeal(s: str=None, rectus: bool=True, source=None) -> str:
    """ The safety pig will appear when there is trouble. """
    tombstone(str)
    return

    for raster in pig:
        if not rectus:
            print(raster.replace(RED, "").replace(LIGHT_BLUE, "").replace(REVERT, ""))
        else:
            print(raster)

    if s:
        postfix = " from " + source if source else ''
        s = (now_as_string() +
             " Eeeek! It is my job to give you the following urgent message" + postfix + ": \n\n<<< " +
            str(s) + " >>>\n")
    tombstone(s)
    return s


def stalk_and_kill(process_name:str) -> bool:
    """
    This function finds other processes who are named canoed ... and
    kills them by sending them a SIGTERM.

    returns True or False based on whether we assassinated our 
        ancestral impostors. If there are none, we return True because
        in the logical meaning of "we got them all," we did.
    """

    tombstone('Attempting to remove processes beginning with ' + process_name)
    # Assume all will go well.
    got_em = True

    for pid in pids_of(process_name, True):
        
        # Be nice about it.
        try:
            os.kill(pid, signal.SIGTERM)
        except:
            tombstone("Process " + str(pid) + " may have terminated before SIGTERM was sent.")
            continue

        # wait two seconds
        time.sleep(2)
        try:
            # kill 0 will fail if the process is gone
            os.kill(pid, 0) 
        except:
            tombstone("Process " + str(pid) + " has been terminated.")
            continue
        
        # Darn! It's still running. Let's get serious.
        os.kill(pid, signal.SIGKILL)
        time.sleep(2)
        try:
            # As above, kill 0 will fail if the process is gone
            os.kill(pid, 0)
            tombstone("Process " + str(pid) + " has been killed.")
        except:
            continue
        tombstone(str(pid) + " is obdurate, and will not die.")
        got_em = False
    
    return got_em


####
# T
####

def this_function():
    """ Takes the place of __function__ in other languages. """

    return inspect.stack()[1][3]


def this_is_the_time(schedule:list) -> bool:
    """
    returns True if *now* is in the schedule, False otherwise.
    """
    t = crontuple_now()
    # tombstone([str(_) for _ in [t.minute, t.hour, t.day, t.month, t.isoweekday]])
    # tombstone(str(schedule))

    return ((t.minute in schedule[0]) and
            (t.hour in schedule[1]) and
            (t.day in schedule[2]) and
            (t.month in schedule[3]) and
            (t.isoweekday() % 7 in schedule[4]))


def this_line(level: int=1, invert: bool=True) -> int:
    """ returns the line from which this function was called.

    level -- generally, this value is one, meaning that we
    want to use the stack frame that is one-down from where we
    are. In some cases, the value "2" makes sense. Take a look
    at CanoeObject.set_error() for an example.

    invert -- Given that the most common use of this function
    is to generate unique error codes, and that error codes are
    conventionally negative integers, the default is to return
    not thisline, but -(thisline)
    """
    cf = inspect.stack()[level]
    f = cf[0]
    i = inspect.getframeinfo(f)
    return i.lineno if not invert else (0 - i.lineno)


def time_match(t, set_of_times:list) -> bool:
    """
    Determines if the datetime object's parts are all in the corresponding
    sets of minutes, hours, etc.
    """
    return   ((t.minute in set_of_times[0]) and
              (t.hour in set_of_times[1]) and
              (t.day in set_of_times[2]) and
              (t.month in set_of_times[3]) and
              (t.weekday() in set_of_times[4]))


def tombstone(args:Any=None) -> Tuple[int, str]:
    """
    Print out a message, data, whatever you pass in, along with
    a timestamp and the PID of the process making the call. 
    Along with printing it out, it returns it.
    """

    i = str(AX()).rjust(4,'0')
    a = i + " " + now_as_string() + " :: " + str(os.getpid()) + " :: "

    sys.stderr.write(a)
    if isinstance(args, str):
        sys.stderr.write(args + "\n")
    elif isinstance(args, list) or isinstance(args, dict):
        sys.stderr.write("\n")
        for _ in args:
            sys.stderr.write(str(_) + "\n")
        sys.stderr.write("\n")
    else:
        pass
        # p = pp.PrettyPrinter(indent=4, width=512, stream=sys.stderr)
        # p.pprint(formatted_stack_trace())

    sys.stderr.flush()

    # Return the info for use by CanoeDB.tombstone()
    return i, a+str(args)
    

std_ignore = [ signal.SIGCHLD, signal.SIGHUP, signal.SIGINT, signal.SIGPIPE, signal.SIGUSR1, signal.SIGUSR2 ]
allow_control_c = [ signal.SIGCHLD, signal.SIGPIPE, signal.SIGUSR1, signal.SIGUSR2 ]
std_die = [ signal.SIGQUIT, signal.SIGABRT ]
def trap_signals(ignore_list:list=std_ignore,
                 die_list:list=std_die):
    """
    There is no particular reason for these operations to be in a function,
    except that if this code moves to Windows it makes sense to isolate
    them so that they may better recieve the attention of an expert.
    """
    global bad_exit
    atexit.register(bad_exit)
    for _ in std_ignore: signal.signal(_, signal.SIG_IGN)
    for _ in std_die: signal.signal(_, bad_exit)

    tombstone("signals hooked.")



def type_and_text(e:Exception) -> str:
    """
    This is not the most effecient code, but by the time this function
    is called, something has gone wrong and performance is unlikely
    to be a relevant point of discussion.
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    a = traceback.extract_tb(exc_traceback)
    
    s = []
    s.append("Raised " + str(type(e)) + " :: " + str(e))
    for _ in a:
        s.append(" at file/line " + 
            str(_[0]) + "/" + str(_[1]) + 
            ", in fcn " + str(_[2]))

    return s


####
# U
####

def unwhite(s: str) -> str:
    """ Remove all non-print chars from string. """
    t = []
    for c in s.strip():
        if c in string.printable:
            t.append(c)
    return ''.join(t)


UR_ZERO_DAY = datetime.datetime(1830, 8, 1)
def urdate(dt:datetime.datetime = None) -> int:
    """
    This is something of a pharse. Instead of calculating days from 
    1 Jan 4713 BCE, I decided to create a truly UR calendar starting
    from 1 August 1830 CE. After all, no dates before then could be 
    of any importance to us. 

    Why August? August 1 1830 was a Sunday, so we don't have to do
    anything fancy to get day of the week. For any urdate, urdate%7 
    is the weekday where Sunday is a zero.
    """
    if dt is None: dt = datetime.datetime.today()
    return (dt - UR_ZERO_DAY).days
    

####
# V
####

def valid_item_name(s:str) -> bool:
    """ Determines if s is a valid item name (according to Oracle)

    s -- the string to test. s gets trimmed of white space.
    returns: - True if this is a valid item name, False otherwise.
    """
    return re.match("^[A-Za-z_.]+$", s.strip()) != None


def version(full:bool = True) -> str:
    """
    Do our best to determine the git commit ID ....
    """
    try:
        v = subprocess.check_output(
            ["/opt/rh/git19/root/usr/bin/git", "rev-parse", "--short", "HEAD"],
            universal_newlines=True
            ).strip()
        if not full: return v
    except:
        v = 'unknown'
    else:
        mods = subprocess.check_output(
            ["/opt/rh/git19/root/usr/bin/git", "status", "--short"],
            universal_newlines=True
            ) 
        if mods.strip() != mods: 
            v += (", with these files modified: \n" + str(mods))
    finally:
        return v
        

####
# W
####

def wall(s: str):
    """ Send out a notification on the system. """
    return subprocess.call(['wall "' + s + '"'])


def urutils_main(): return 'hello world'


if __name__ == "__main__":
    assert(is_phone_number("8043992699") == True)
    assert(is_phone_number("80IBURNEXA") == False)
    assert(normalize_phone_number("+1.804.399.2699") == "18043992699")

    try:
        raise Exception("yo! this is a test of dump_exception.", this_line())
    except Exception as e:
        print(dump_exception(e))

    try:
        x = get_ssh_host_info()
    except Exception as e:
        print(dump_exception(e))
    else:
        for k in x.get_hostnames():
            print(k + "=>" + str(x.lookup(k)))


    print(str(get_ssh_host_info('mate')))

    #Lots of datetime tests with date_filter

    #Utility function used for following date filter tests
    def text_is(t,s):
        f = date_filter(t)
        print(f)
        return f == s

    print("\n--- Begin Date Filter Tests ---")
    today = datetime.datetime.today()
    YYYY = today.strftime("%Y")
    Yq = today.strftime("%-y")
    MM = today.strftime("%m")
    Mq = today.strftime("%-m")
    bbb = today.strftime("%b").upper()
    DD = today.strftime("%d")
    Dq = today.strftime("%-d")
    hh = today.strftime("%H")
    mm = today.strftime("%M")
    ss = today.strftime("%S")

    assert(text_is("File{YYYY}","File{}".format(YYYY)))
    assert(text_is("File{YYYY}.txt", "File{}.txt".format(YYYY)))
    assert(text_is("{YYYY}File","{}File".format(YYYY)))
    assert(text_is("File{Y?}","File{}".format(Yq)))
    assert(text_is("File{Y?}.txt", "File{}.txt".format(Yq)))
    assert(text_is("{Y?}File","{}File".format(Yq)))
    assert(text_is("File{MM}","File{}".format(MM)))
    assert(text_is("File{MM}.txt", "File{}.txt".format(MM)))
    assert(text_is("{MM}File","{}File".format(MM)))
    assert(text_is("File{M?}","File{}".format(Mq)))
    assert(text_is("File{M?}.txt", "File{}.txt".format(Mq)))
    assert(text_is("{M?}File","{}File".format(Mq)))
    assert(text_is("File{bbb}","File{}".format(bbb)))
    assert(text_is("File{bbb}.txt", "File{}.txt".format(bbb)))
    assert(text_is("{bbb}File","{}File".format(bbb)))
    assert(text_is("File{DD}","File{}".format(DD)))
    assert(text_is("File{DD}.txt", "File{}.txt".format(DD)))
    assert(text_is("{DD}File","{}File".format(DD)))
    assert(text_is("File{D?}","File{}".format(Dq)))
    assert(text_is("File{D?}.txt", "File{}.txt".format(Dq)))
    assert(text_is("{D?}File","{}File".format(Dq)))
    assert(text_is("File{hh}","File{}".format(hh)))
    assert(text_is("File{mm}.txt", "File{}.txt".format(mm)))
    assert(text_is("{mm}File","{}File".format(mm)))
    assert(text_is("File{mm}","File{}".format(mm)))
    assert(text_is("File{ss}.txt", "File{}.txt".format(ss)))
    assert(text_is("{ss}File","{}File".format(ss)))
    assert(text_is("File{ss}","File{}".format(ss)))

    print("")
    print("Sanity checks passed")
else:
    # print(str(os.path.abspath(__file__)) + " compiled.")
    print("*", end="")

