import pdb
import socket
import sys
import os
import selectors
import fcntl
import argparse

from .config import current_config as pytb_config

"""
A remote debugging module for the python debugger pdb
"""


class Rdb(pdb.Pdb):

    _std_streams = ["stdin", "stdout", "stderr"]
    """
    streams to redirect to the socket on connection
    """

    _session = None
    """
    A global session of the debugger. It is used to keep alive the session between multiple calls to 
    set_trace() when the session originally was continued by the user
    """

    def __init__(self, host=None, port=None, patch_stdio=None, **kwargs):
        """

        :param host: Host interface to bind the remote socket to. 
            If None, the key `bind_to` from the current :class:`pytb.config.Config`s `[rdb]` section is used
        :param port: Port to listen for incoming connections
            If None, the key `port` from the current :class:`pytb.config.Config`s `[rdb]` section is used
        :param patch_stdio: redirect this process' stdin, stdout and stderr to the remote debugging client
            If None, the key `bind_to` from the current :class:`pytb.config.Config` s `[rdb]` section is used
        :param **kwargs: passed to the parent Pdb class, except ``stdin`` and ``stdout`` are always overwritten by the remote socket
        """

        Rdb._session = self

        # load the parameters from the config
        config = pytb_config["rdb"]
        host = config.get("bind_to") if host is None else host
        port = int(config.get("port")) if port is None else port
        patch_stdio = config.get("patch_stdio") if patch_stdio is None else patch_stdio

        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        listen_socket.bind((host, port))
        print(
            f"Started Remote debug session on {host}:{port}. Waiting for connection...",
            file=sys.__stderr__,
        )
        listen_socket.listen(1)
        connection, address = listen_socket.accept()

        self.connection_file = connection.makefile("rw")
        kwargs["stdin"] = self.connection_file
        kwargs["stdout"] = self.connection_file
        super().__init__(**kwargs)

        self.stdio_patched = patch_stdio
        if patch_stdio:
            self.original_streams = {}
            for stream in Rdb._std_streams:
                self.original_streams[stream] = getattr(sys, stream)
                setattr(sys, stream, self.connection_file)

        self.prompt = f"RDB@{socket.gethostname()}:{port} >>> "

    def _flush_outputs(self):
        """
        Flush all currently installed stdio streams forwarded to the socket or not
        """
        for stream in Rdb._std_streams:
            getattr(sys, stream).flush()

    def _cleanup(self):
        """
        Quit from the debugger. The remote connection is closed 
        and the stdio streams are restored to their original state 
        """
        self._flush_outputs()

        if self.stdio_patched:
            for stream in Rdb._std_streams:
                setattr(sys, stream, self.original_streams[stream])

        self.stdin = sys.stdin
        self.stdout = sys.stdout

        self.connection_file.close()

        Rdb._session = None

    def do_continue(self, arg):
        self._flush_outputs()
        return super().do_continue(arg)

    do_c = do_cont = do_continue

    def do_EOF(self, arg):
        self._cleanup()
        return super().do_EOF(arg)

    def do_quit(self, arg):
        self._cleanup()
        return super().do_quit(arg)

    do_q = do_exit = do_quit


def set_trace(host=None, port=None, patch_stdio=False):
    """
    Opens a remote PDB on the specified host and port if no session is running.
    If a session is already running (was started previously and a client is still connected)
    the session is reused instead.

    :param patch_stdio: When true, redirects stdout, stderr and stdin to the remote socket.
    """

    if Rdb._session is None:
        if host is None:
            host = os.environ.get("REMOTE_PDB_HOST", None)
        if port is None:
            port = os.environ.get("REMOTE_PDB_PORT", None)
            if port is not None:
                port = int(port)

        Rdb._session = Rdb(host=host, port=port, patch_stdio=patch_stdio)

    Rdb._session.set_trace(frame=sys._getframe().f_back)


_previous_breakpoint_hook = None


def install_hook():
    """
    Installs the remote debugger as standard debugging method and calls it when using the builtin `breakpoint()`
    """
    _previous_breakpoint_hook = sys.breakpointhook
    sys.breakpointhook = set_trace


def uninstall_hook():
    """
    Restore the original state of sys.breakpointhook. 
    If :meth:`install_hook` was never called before, this is a noop
    """
    if _previous_breakpoint_hook is not None:
        sys.breakpointhook = _previous_breakpoint_hook


class RdbClient:
    """
    A simple ``netcat`` like socket client that can be used as a convenience 
    wrapper to connect to a remote debugger session.

    If  `host` or  `port` are unspecified, they are laoded from the current :class:`pytb.config.Config` s `[rdb]` section
    """

    _selector = selectors.DefaultSelector()

    def __init__(self, host=None, port=None):

        # load the parameters from the config
        config = pytb_config["rdb"]
        host = config.get("host") if host is None else host
        port = int(config.get("port")) if port is None else port

        self.socket = socket.create_connection((host, port))

        self.socket.setblocking(False)

        # make stdin non-blocking to multiplex reading with the socket
        orig_fl = fcntl.fcntl(sys.stdin, fcntl.F_GETFL)
        fcntl.fcntl(sys.stdin, fcntl.F_SETFL, orig_fl | os.O_NONBLOCK)

        # install the mulitplexing selector on the socket and stdin (stdout still is blocking)
        RdbClient._selector.register(
            self.socket, selectors.EVENT_READ | selectors.EVENT_WRITE, self._handle_io
        )
        RdbClient._selector.register(sys.stdin, selectors.EVENT_READ, self._handle_io)

        # create an empty string buffer
        self.socketbuf = ""

        while True:
            # wait for I/O
            events = RdbClient._selector.select()
            for key, mask in events:
                callback = key.data
                callback(key.fileobj, mask)

    def _handle_io(self, stream, mask):
        if stream is self.socket:
            if mask & selectors.EVENT_READ:
                encoding = sys.stdout.encoding
                sys.stdout.write(self.socket.recv(1024).decode(encoding, "ignore"))
            elif mask & selectors.EVENT_WRITE:
                if self.socketbuf:
                    sent = self.socket.send(self.socketbuf.encode(sys.stdout.encoding))
                    self.socketbuf = self.socketbuf[sent:]
        elif stream is sys.stdin:
            self.socketbuf += sys.stdin.read()
