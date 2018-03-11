#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Beachhead is a program that allows interactive operation of
the paramiko stack. The purpose is to diagnose, triage, and
log connectivity problems.
"""
__author__ = 'George Flanagin'
__copyright__ = 'Copyright 2017, University of Richmond and George Flanagin'
__credits__ = None
__version__ = '0.1'
__maintainer__ = 'George Flanagin'
__email__ = 'me@georgeflanagin.com'
__status__ = 'PyRVA demonstration'
__license__ = 'MIT'
__required_version__ = (3,5)

import getpass
import os
import sys
import typing
from   typing import *

""" 
This program is intended as a standalone, so let's see if we have 
everything we need.
"""

if sys.version_info < __required_version__:
    uu.tombstone('This program requires Python {} or greater.'.format(__required_version__))
    sys.exit(os.EX_SOFTWARE)

required_modules = sorted([
    'setproctitle', 'simplejson', 'psutil', 'paramiko', 'croniter',
    'dateutil', 'shlex', 'shutil', 'sortedcontainers'])

import imp
missing_modules = set()
for _ in required_modules:
    try:
        imp.find_module(_)
    except ImportError as e:
        missing_modules.add(_)

if len(missing_modules):
    print("Hey! You don't have everything you need. You seem to be missing\n" +
        ", ".join(missing_modules))
    sys.exit(os.EX_SOFTWARE)
    

# Builtins
import argparse
import cmd
import glob
import json
import logging
import os
import pprint as pp
import setproctitle
import socket
import subprocess
import sys
import time
import typing
from   typing import *

# Paramiko
import paramiko 
from   paramiko import SSHClient, SSHConfig, SSHException

import fname
import jparse
import urutils as uu

import pdb
run_debugger = False

members = ['kex', 'ciphers', 'digests', 'compression', 'key_types']

class SmallHOP:

    __slots__ = [
        'my_host', 'user', 'remote_host', 'remote_port', 'ssh_info',
        'auth_timeout', 'banner_timeout', 'tcp_timeout', 'sock_type', 'sock_domain',
        'password', 'sock', 'transport', 'security', 'channel',
        'client', 'sftp', 'error'
        ]

    def __init__(self, do_log:bool=False):
        # Identification members
        self.my_host = socket.getfqdn().replace('-','.')
        self.user = uu.me()
        self.remote_host = ""
        self.remote_port = 0
        self.ssh_info = None

        # Performance parameters.
        self.auth_timeout = 1.0
        self.banner_timeout = 1.0
        self.tcp_timeout = 1.0

        # Socket types
        self.sock_type = socket.SOCK_STREAM
        self.sock_domain = socket.AF_INET

        # Connection parameters.
        self.password = None
        self.sock = None
        self.transport = None
        self.security = {}
        self.channel = None
        self.client = None
        self.sftp = None

        # Most recent error.
        self.error = None
        if do_log:
            self.do_logging('on')

    
    def __bool__(self) -> bool: 
        """ Is the sock open in a non-error state? """

        return self.error is None and self.sock is not None


    def __str__(self) -> str:
        """ Print the current connection """

        return "" if not self else "{}:{} {}".format(
            self.remote_host, self.remote_port, self.error_msg())


    def close(self) -> None:
        """ Close everything and reset values for a second use. """

        if self.sftp: self.sftp.close(); self.sftp = None
        if self.channel: self.channel.close(); self.channel = None
        if self.transport: self.transport.close(); self.transport = None
        if self.client: self.client.close(); self.client = None
        if self.sock: self.sock.close(); self.sock = None


    def debug_level(self, level:int=None) -> int:
        """
        Manipulate the logging level.
        """

        if level is None:
            return logging.getLogger('paramiko').getEffectiveLevel()      
        else:
            logging.getLogger('paramiko').setLevel(level)
            return self.debug_level()  


    def error_msg(self) -> str:
        return str(self.error)


    def open_channel(self, channel_type:str="session") -> bool:
        """
        Acquire a channel of the desired type. "session" is the default.
        """
        self.error = None
        channel_types = {
            "session":"session", 
            "forward":"forwarded-tcpip", 
            "direct":"direct-tcpip", 
            "x":"x11"
            }

        if data not in channel_types.keys() and data not in channel_types.values():
            self.error = 'unknown channel type: {}'.format(data)
            return False

        try:
            self.channel = self.transport.open_channel(data)
        except Exception as e:
            self.error = uu.type_and_text(e)
        finally:
            return self.error is not None


    def open_session(self) -> bool:
        """
        Attempt to create an SSH session with the remote host using
        the socket, transport, and channel that we [may] have already
        openend.
        """
        global members

        self.error = None
        self.client = SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)

        try:
            username=self.ssh_info.get('user', getpass.getuser())
            if not self.password:
                self.client.connect(self.ssh_info['hostname'],
                    int(self.ssh_info['port']),
                    username=username,
                    key_filename=self.ssh_info['identityfile'],
                    sock=self.sock)        

            else:
                self.client.connect(self.ssh_info['hostname'], 
                    int(self.ssh_info['port']), 
                    username=username, 
                    password=self.password,
                    sock=self.sock)

        except paramiko.ssh_exception.BadAuthenticationType as e:
            self.error = str(e)

        except TypeError as e:
            uu.tombstone(red('Socket not open.'))
            self.error = -1

        except Exception as e:
            self.error = uu.type_and_text(e)

        else:
            self.open_transport()
            opts = self.transport.get_security_options()          
            self.security = { k:list(getattr(opts, k, None)) for k in members }
            self.security['host_key'] = self.transport.get_remote_server_key().get_base64()
            self.security['version'] = self.transport.remote_version

        finally:
            return self.error is None


    def open_sftp(self, data:list=[]) -> bool:
        """
        Open an sftp connection to the remote host.
        """
        self.error = None
        try:
            self.sftp = paramiko.SFTPClient.from_transport(self.transport)

        except Exception as e:
            self.error = uu.type_and_text(e)

        finally:
            return self.error is None


    def open_socket(self, host:str, port:int=None) -> bool:
        """
        Attemps to open a new socket with the current parameters.
        """
        self.error = None
        self.ssh_info = uu.get_ssh_host_info(host)
        if not self.ssh_info: 
            self.error = 'unknown host'
            return False

        hostname = self.ssh_info['hostname'] 
        try:
            port = int(port)
        except:
            port = int(self.ssh_info.get('port', 22))

        self.sock = socket.socket(self.sock_domain, self.sock_type)
        try:
            self.sock.settimeout(self.tcp_timeout)
            self.sock.connect((hostname,port))
        except socket.timeout as e:
            self.error = 'timeout of {} seconds exceeded.'.format(self.tcp_timeout)
        except Exception as e:
            self.error = uu.type_and_text(e)
        else:
            self.remote_host = hostname
            self.remote_port = port
        
        return self.error is None


    def open_transport(self, data:str="") -> bool:
        """
        Creates a transport layer from an open/active ssh session.
        """
        self.error = None
        if not self.client:
            self.error = 'no open session for transport'
            return False

        try:
            self.transport = self.client.get_transport()

        except Exception as e:
            self.error = uu.type_and_text(e)

        finally:
            return self.error is None
            
    
    def timeouts(self) -> tuple:
        return self.tcp_timeout, self.auth_timeout, self.banner_timeout


########################################################

def blue(s:str) -> str:
    return uu.BLUE + str(s) + uu.REVERT


def red(s:str) -> str:
    return uu.YELLOW + str(s) + uu.REVERT


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
    indent + '                           /                     '+uu.YELLOW + 'BEACHHEAD' + uu.REVERT,
    indent + '                /\\________/__/\\ ',
    indent + '   ~~~    ~^~~~~\\________/____/~~~     ooo000000000000000000000000',
    indent + '               ~~~~  ~~ /~          oooooooo0000000oooo00000000000',
    indent + '....................~~^/~........^^o0o0ooo000o000o00o00o00o00o00oo',
    indent + '..<°))))><..                                        o00ooo0ooooo00',
    indent + '............  '+ uu.RED + 'From the people who brought you Canøe.' + uu.REVERT + '  000o00ooo0o0',
    indent + '.............                                        oo00000oooooo',
    indent + '...................><{{{°>..............................oooxxx0000',
    indent + '',
    indent + uu.RED + '  Type `help general` for more information.' + uu.REVERT,
    ' ',
    '='*80,
    ""
]

__default_config__ = 'beachhead.json'
class Beachhead: pass
class Beachhead(cmd.Cmd):
    """
    Beachhead is not a tool for the weak.
    """    

    use_rawinput = True
    doc_header = 'To get a little overall guidance, type `help general`'
    intro = "\n".join(banner)

    def __init__(self, do_log:bool):
        
        cmd.Cmd.__init__(self)
        Beachhead.prompt = "\n[beachhead]: "
        self.hop = SmallHOP(do_log)
        self.cfg = {}
        self.cfg_file = None

    
    def preloop(self) -> None:
        """
        Get the config (if any). This function updates the self.cfg_file class member
            with the full file name of the one that we will use.
        """
        setproctitle.setproctitle('beachhead')

        default_ssh_config_file = '~/.ssh/config'
        f = fname.Fname(default_ssh_config_file)
        if not f:
            uu.tombstone('You do not seem to have an ssh config file. This program')
            uu.tombstone('may not be very useful.')

        try:
            for d in [ os.environ.get(_, "") for _ in [ 'PWD' ] ]:
                for this_dir, sub_dirs, files in os.walk(d):
                    for f in files:
                        if f == __default_config__: 
                            self.cfg_file = os.path.join(d, this_dir, f)
                            raise StopIteration

        except StopIteration as e:
            try:
                jp = jparse.JSONReader()
                self.cfg = jp.attach_IO(self.cfg_file, True).convert()
                uu.tombstone('Using config info read from {}'.format(self.cfg_file))

            except Exception as e:
                uu.tombstone(str(e))
                uu.tombstone('{} failed to compile.'.format(self.cfg_file))

        except Exception as e:
            uu.tombstone(uu.type_and_text(e))
            uu.tombstone('Something really bad happened.')
            raise

        else:
            uu.tombstone('No config file found.')

    def default(self, data:str="") -> None:
        uu.tombstone(red('unknown command {}'.format(data)))
        self.do_help(data)


    """ ***********************************************************************************
    These are our console commands.
    *********************************************************************************** """

    def do_close(self, data="") -> None:
        """
        Close the open socket connection (if any)
        """
        if self.hop: self.hop.close()
        else: uu.tombstone(blue('nothing to do'))


    def do_debug(self, data:str="") -> None:
        """
        debug [ value ]

            With no parameter, this function prints the current debug level (as if
            you cannot tell already). Otherwise, set the level.
        """
        if not len(data):
            uu.tombstone(blue('debug level is {}'.format(self.hop.debug_level())))
            return

        logging_levels = {
            "CRITICAL":"50",
            "ERROR":"40",
            "WARNING":"30",
            "INFO":"20",
            "DEBUG":"10",
            "NOTSET":"0" 
            }

        data = data.strip().upper()
        if data not in logging_levels.keys() and data not in logging_levels.values():
            uu.tombstone(red('not sure what this level means: {}'.format(data)))
            return
            
        try:
            level = int(data)
        except:
            level = int(logging_levels[data])
        finally:
            self.hop.debug_level(level)
            


    def do_do(self, data:str="") -> None:
        """
        do { something }

            attempt to exit a command by stuffing the text through the channel
        """
        if not self.hop.channel or not data: 
            self.do_help('do')
            return

        try:
            uu.tombstone(blue('attempting remote command {}'.format(data)))
            in_, out_, err_ = self.hop.channel.exec_command(data)

        except KeyboardInterrupt as e:
            uu.tombstone(blue('aborting. Control-C pressed.'))

        except Exception as e:
            uu.tombstone(red(uu.type_and_text(e)))

        else:
            out_.channel.recv_exit_status();
            uu.tombstone(blue(out_.readlines()))

        finally:
            self.hop.open_channel()


    def do_error(self, data:str="") -> None:
        """
        error [reset]

        [re]displays the error of the connection, and optionally resets it
        """
        uu.tombstone(blue(self.hop.error))
        if 'reset'.startswith(data.strip().lower()): self.hop.error = None


    def do_exit(self, data:str="") -> None:
        """
        exit:
            leave very abruptly.
        """
        sys.exit(os.EX_OK)


    def do_general(self, data:str="") -> None:
        """
        Beachhead, version _ (do you really care?). 

        This program allows you to explore network connections step-by-step,
        using the Python 3 library named `paramiko`. To make (or attempt to
        make) a connection to a remote host, the following is recommended:

        hosts  <- This will give a list of "known hosts" based on the contents
            of your `~/.ssh/config file` (or equivalent).

        open socket host [port]  <- Specify your target, and create a connection.
            The port defaults to 22.

        [set password AbraCadabra] <- Only if you need it; keys don't require
            a password.

        open session <- Using the info from ~/.ssh/config
        
        Now, if you want to execute a command on the remote host, you will need
        a channel. If you want to transfer a file (something we do a lot of), you
        will need an sftp client. Unsurprisingly, the commands are:

        open channel 
        open sftp
        """
        print(self.do_general.__doc__)


    def do_get(self, data:str="") -> None:
        """
        get a file from the remote host.

        Syntax: get filename
        """
        if not self.hop.sftp:
            uu.tombstone(red('sftp channel is not open.'))
            return

        if not data:
            self.do_help('get')
            return

        start_time = time.time()
        OK = self.hop.sftp.get(data, Fname(data).fname)
        stop_time = time.time()
        if OK: uu.tombstone('success')
        else: uu.tombstone('failure {}'.format(self.hop.error_msg()))
        uu.tombstone('elapsed time: {}'.format(elapsed_time(stop_time, start_time)))


    def do_hosts(self, data:str="") -> None:
        """
        hosts:
            print a list of the available (known) hosts
        """
        uu.tombstone("\n"+blue("\n".join(sorted(list(uu.get_ssh_host_info('all'))))))


    def do_logging(self, data:str="") -> None:
        """
        Usage:
    
            logging { on | off }

        turns logging (to $PWD/beachhead.log) on or off. No error is
        created when logging is on and you ask to turn it on, etc.

        If you would like to specify a different logfile, there are 
        two solutions.

        [1] Symbolic links:
            rm -f $PWD/beachhead.log
            ln -s yourfile $PWD/beachhead.log

        [2] Use a different program.
        """
        states = {
            "on":True,
            "off":False
            }


        if not data:
            self.do_help('logging')
            return

        try:
            state = states.get(data.lower(), None)
            if state is None: raise StopIteration from None

        except StopIteration as e:
            self.do_help('logging')
            return

        except Exception as e:
            uu.tombstone(uu.type_and_text(e))
            return

        if state:
            logging.getLogger("paramiko").setLevel(logging.WARNING)
            paramiko.util.log_to_file("beachhead.log")
        else:
            logging.getLogger("paramiko").setLevel(logging.NOTSET)

        return
        

    def do_open(self, data:str="") -> None:
        """
        open { 
                socket { host port } |
                session |
                channel [ type ] |
                sftp
             }

        Usually, the order of opening is:

            1. get a *socket* connection.
            2. create an ssh *session*.
            3. open a *channel* in the established transport layer.
        """

        if not len(data): 
            self.do_help('open')
            return

        data = data.strip().split()
        f = getattr(self, '_do_'+data[0], None)

        if f: f(data[1:]) 
        else: uu.tombstone(red('no operation named {}'.format(data)))


    def do_put(self, data:str="") -> None:
        """
        put a file onto the remote host.

        Syntax: put filename

            NOTE: filename can be a wildcard spec.
        """
        if not self.hop.sftp:
            uu.tombstone(red('sftp channel is not open.'))
            return

        if not data:
            uu.tombstone(red('you have to send something ...'))
            self.do_help('put')
            return

        files = glob.glob(data)
        if not files:
            uu.tombstone(red('no file[s] named {}'.format(data)))
            return

        start_time = time.time()
        OK = None
        for f in files:
            try:
                OK = self.hop.sftp.put(f.fqn, f.fname)
            except Exception as e:
                uu.tombstone(red(uu.type_and_text(e)))

            stop_time = time.time()
            if OK: uu.tombstone('success')
            else: uu.tombstone('failure {}'.format(self.hop.error_msg()))

        uu.tombstone('elapsed time: '.format(elapsed_time(stop_time, start_time)))


    def do_quit(self, data:str="") -> None:
        """
        quit:
            close up everything gracefully, and then exit.
        """
        if self.hop.sock:
            self.hop.sock.close()
        os.closerange(3,1024)
        self.do_exit(data)


    def do_send(self, data:str="") -> None:
        """
        send { file filename | string }

        Sends stuff over the channel.
        """
        if not self.hop.channel: 
            uu.tombstone(red('channel not open.'))
            self.do_help('send')
            return

        if data.startswith('file'):
            try:
                _, filename = data.split()
                f = fname.Fname(filename)
                if f: data=f()
            except Exception as e:
                uu.tombstone(red(uu.type_and_text(e)))
            
        try:
            i = self.hop.channel.send(data)
            uu.tombstone(blue('sent {} bytes.'.format(i)))

        except KeyboardInterrupt:
            uu.tombstone(blue('aborting. Control-C pressed.'))

        except Exception as e:
            uu.tombstone(red(uu.type_and_text(e)))
            
        finally:
            self.hop.open_channel()


    def do_setpass(self, data:str="") -> None:
        """
        setpass [password]
        
            sets, displays, or clears ('none') the password to be used.
        """
        data = data.strip()

        if data.lower() == 'none': self.hop.password = None
        elif not data: uu.tombstone(blue('password is set to {}'.format(self.hop.password)))
        else: self.hop.password = data        


    def do_setsockdomain(self, data:str="") -> None:
        """
        setsockdomain [{ af_inet | af_unix }]

            af_inet -- internet sockets
            af_unix -- a socket on local host that most people call a 'pipe'
        """

        if not data: uu.tombstone(blue('socket domain is {}'.format(self.hop.sock_domain))); return
        data = data.strip().lower()

        if data == 'af_inet': self.hop.sock_domain = socket.AF_INET
        elif data == 'af_unix': self.hop.sock_domain = socket.AF_UNIX
        else: uu.tombstone(blue('unknown socket domain: {}'.format(data)))


    def do_setsocktype(self, data:str="") -> None:
        """
        setsocktype [{ stream | dgram | raw }]

            stream -- ordinary TCP socket
            dgram  -- ordinary UDP socket
            raw    -- bare metal 
        """
        sock_types = {'stream':socket.SOCK_STREAM, 'dgram':socket.SOCK_DGRAM, 'raw':socket.SOCK_RAW }
        if not data: uu.tombstone('socket type is {}'.format(self.hop.sock_type)); return

        try:
            self.hop.sock_type = sock_types[data.strip().lower()]                

        except:
            uu.tombstone(blue('unknown socket type: {}'.format(data)))


    def do_settimeout(self, data:str="") -> None:
        """
        settimeout [ { tcp | auth | banner } {seconds} ]

        Without parameters, settimeout will show the current socket timeout values.
        Otherwise, set it and don't forget it.
        """
        if not data: 
            uu.tombstone('timeouts (tcp, auth, banner): ({}, {}, {})'.format(
                self.hop.tcp_timeout, self.hop.auth_timeout, self.hop.banner_timeout))
            return

        data = data.strip().split()
        if len(data) < 2:
            uu.tombstone(red('missing timeout value.'))
            self.do_help('settimeout')
            return

        try:
            setattr(self.hop, data[0]+'_timeout', float(data[1]))
        except AttributeError as e:
            uu.tombstone(red('no timeout value for ' + data[0]))
        except ValueError as e:
            uu.tombstone(red('bad value for timeout: {}' + data[1]))
        else:
            self.do_settimeout()


    def do_show(self, what:str="") -> None:
        """
        Usage: 

            show { config | version }
        """
        if not what: self.do_help('show'); return

        f = getattr(self, "_do_" + what, None)
        try:
            f()
        except:
            self.do_help('show')


    def do_status(self, data:str="") -> None:
        """
        status

            displays the current state of the connection.
        """
        global members

        uu.tombstone(blue("debug level: {}".format(self.hop.debug_level())))
        if not self.hop.sock: uu.tombstone('not connected.'); return

        uu.tombstone(blue("local end:     {}".format(self.hop.sock.getsockname())))
        uu.tombstone(blue("remote end:    {}".format(self.hop.sock.getpeername())))
        uu.tombstone(blue("type/domain:   {} / {}".format(self.hop.sock_type, self.hop.sock_domain)))
        uu.tombstone(blue("ssh session:   {}".format(self.hop.client)))
        uu.tombstone(blue("transport:     {}".format(self.hop.transport)))
        uu.tombstone(blue("sftp layer:    {}".format(self.hop.sftp)))
        uu.tombstone(blue("channel:       {}".format(self.hop.channel)))
        try:
            banner=self.hop.transport.get_banner().decode('utf-8')
        except:
            banner="no banner found"
        uu.tombstone(blue("banner:        {}".format(banner)))
        uu.tombstone(blue("*** security info: ***"))
        for _ in self.hop.security.keys():
            uu.tombstone(blue("{} : {}").format(_,self.hop.security.get(_, None)))


    def do_save(self, data:str="") -> None:
        """
        save [ additional-file-name ]
        
            Saves the current configuration, including information about
            the current host. If you supply a filename, that file will contain
            a duplicate copy of this data.

        The configuration is written as a JSON file, indented 4 spaces per
            level, with the host names sorted alphabetically. The kex-es and
            ciphers are listed in the order the host perfers them. 
        """

        try:
            with open(data, 'w') as f:
                json.dump(self.cfg, f, sort_keys=True, indent=4)
                uu.tombstone('Duplicate config file written to {}'.format(data))
        except:
            pass

        old_sec_info = self.cfg.get(self.hop.remote_host, {})
        new_sec_info = self.hop.security
        if new_sec_info == {}:
            uu.tombstone('No active connection / no data to update.')
            return

        if old_sec_info == new_sec_info: 
            uu.tombstone('Update not required for {}'.format(self.hop.remote_host))
            return

        self.cfg[self.hop.remote_host] = new_sec_info
        with open(self.cfg_file, 'w') as f:
            json.dump(self.cfg, f, sort_keys=True, indent=4)
            uu.tombstone('Update successful. Written to {}'.format(self.cfg_file))


    def do_version(self, data:str="") -> None:
        """
        version

            prints the version
        """
        self._do_version()


    """ ***********************************************************************************
    The following functions cannot be called directly, but rather through "open"
    *********************************************************************************** """

    def _do_channel(self, data:list=[]) -> None:
        """
        channel [ session | forward | direct | x11 ]

            Acquire a channel of the desired type. "session" is the default.
        """
        data = 'session' if not data else data[0].lower()
        channel_types = {"session":"session", "forward":"forwarded-tcpip", 
            "direct":"direct-tcpip", "x":"x11"}

        if data not in channel_types.keys() and data not in channel_types.values():
            uu.tombstone(blue('unknown channel type: {}'.format(data)))
            return

        uu.tombstone(blue('attempting to create a channel of type {}'.format(data)))

        start_time = time.time()
        OK = self.hop.transport.open_channel(data)
        stop_time = time.time()

        if OK: uu.tombstone(blue('success'))
        else: uu.tombstone(red('failed ' + self.hop.error_msg()))

        uu.tombstone(blue('elapsed time: {}'.format(elapsed_time(start_time, stop_time))))


    def _do_version(self) -> None:
        uu.tombstone("This is the only version you will ever need.")
        uu.tombstone("What difference does it make?")
        pass


    def _do_config(self) -> None:
        """
            Prints the currect config.
        """
        pp.pprint(self.cfg)


    def _do_session(self, data:list=[]) -> None:
        """
        session

            Attempt to create an SSH session with the remote host using
            the socket, transport, and channel that we [may] have already
            openend.
        """
        self.hop.client = SSHClient()
        self.hop.client.load_system_host_keys()
        self.hop.client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    
        start_time = time.time()
        OK = self.hop.open_session()
        stop_time = time.time()

        if OK: uu.tombstone(blue('ssh session established.'))
        else: uu.tombstone(red('failed '+self.hop.error_msg()))

        uu.tombstone(blue('elapsed time: {}'.format(elapsed_time(start_time, stop_time))))


    def _do_sftp(self, data:list=[]) -> None:
        """
        Open an sftp connection to the remote host.
        """
        if not self.hop.transport:
            uu.tombstone(red('Transport layer is not open. You must create it first.'))
            return

        uu.tombstone(blue('creating sftp client.'))
        start_time = time.time()
        OK = self.hop.open_sftp()
        stop_time = time.time()

        if OK: uu.tombstone(blue('success'))
        else: uu.tombstone(red('failure '+self.hop.error_msg()))

        uu.tombstone(blue('elapsed time: {}'.format(elapsed_time(start_time, stop_time))))
            

    def _do_socket(self, data:list=[]) -> None:
        """
        Attemps to open a new socket with the current parameters.
        """

        if len(data) < 1: 
            uu.tombstone('nothing to do.')
            return

        elif len(data) == 1:
            data.append(None)

        start_time = time.time()
        OK = self.hop.open_socket(data[0], data[1])
        stop_time = time.time()
        if OK: uu.tombstone(blue('connected.'))
        else: uu.tombstone(self.hop.error_msg())          
        
        uu.tombstone(blue('elapsed time: {}'.format(elapsed_time(start_time, stop_time))))


    def _do_transport(self, data:str="") -> None:
        """
        Creates a transport layer from an open/active ssh session.
        """
        if not self.hop.client:
            uu.tombstone('You must create an ssh session before you can create a transport layer atop it.')
            return

        uu.tombstone(blue('attempting to create a transport layer'))
        start_time = time.time()
        OK = self.hop.open_transport()
        stop_time = time.time()
        if OK: uu.tombstone(blue('success'))
        else: uu.tombstone(red('failed '+self.hop.error_msg()))
        uu.tombstone(blue('elapsed time: {}'.format(elapsed_time(start_time, stop_time))))
        

if __name__ == "__main__":

    subprocess.call('clear',shell=True)
    try:
        do_log = sys.argv[1].lower() == 'log'
    except:
        do_log = False

    while True:
        try:
            Beachhead(do_log).cmdloop()

        except KeyboardInterrupt:
            uu.tombstone("Exiting via control-C.")
            sys.exit(os.EX_OK)

        except Exception as e:
            uu.tombstone(uu.type_and_text(e))
            uu.tombstone(uu.formatted_stack_trace())
            sys.exit(1) 
