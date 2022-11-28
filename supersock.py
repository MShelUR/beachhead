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
import contextlib
import getpass

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


class SuperSock:

    __slots__ = (
        'my_host', 'user', 'remote_host', 'remote_port', 'ssh_info', 
        'auth_timeout', 'banner_timeout', 'tcp_timeout', 'sock_type', 'sock_domain',
        'password', 'sock', 'transport', 'security', 'channel',
        'client', 'sftp', 'error', 'kex', 'ciphers',
        'digests', 'compression', 'key_types', 'sshkeys'
        )

    __values__ = ( "", "", "", 0, {}, 
        0, 0, 0, "tcp", "inet",
        "", socket.socket(), object(), object(), object(),
        object(), object(), int, {}, [],
        [], int, [], [] )

    __defaults__ = dict(zip(__slots__, __values__))

    def __init__(self, do_log:bool=False):
        # Identification members
        self.my_host = socket.getfqdn().replace('-','.')
        self.user = getpass.getuser()
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
            self.error = e
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
            linuxutils.tombstone(red('Socket not open.'))
            self.error = -1

        except Exception as e:
            self.error = e

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
            self.error = e

        finally:
            return self.error is None


    def open_socket(self, host:str, port:int=None) -> bool:
        """
        Attemps to open a new socket with the current parameters.
        """
        self.error = None
        self.ssh_info = netutils.get_ssh_host_info(host)
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
            self.error = e

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
            self.error = e

        finally:
            return self.error is None
            
    
    def timeouts(self) -> tuple:
        return self.tcp_timeout, self.auth_timeout, self.banner_timeout



@trap
def supersock_main(myargs:argparse.Namespace) -> int:
    return os.EX_OK


if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(prog="supersock", 
        description="What supersock does, supersock does best.")

    parser.add_argument('-i', '--input', type=str, default="",
        help="Input file name.")
    parser.add_argument('-o', '--output', type=str, default="",
        help="Output file name")
    parser.add_argument('--nice', type=int, choices=range(0, 20), default=0,
        help="Niceness may affect execution time.")
    parser.add_argument('-v', '--verbose', action='store_true',
        help="Be chatty about what is taking place")


    myargs = parser.parse_args()
    myargs.verbose and linuxutils.dump_cmdline(myargs)
    if myargs.nice: os.nice(myargs.nice)

    try:
        outfile = sys.stdout if not myargs.output else open(myargs.output, 'w')
        with contextlib.redirect_stdout(outfile):
            sys.exit(globals()[f"{os.path.basename(__file__)[:-3]}_main"](myargs))

    except Exception as e:
        print(f"Escaped or re-raised exception: {e}")


