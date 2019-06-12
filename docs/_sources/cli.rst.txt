----------------------
Command Line Interface
----------------------

The toolkit can be run as an executable (e.g. using the ``-m`` switch
of the python command or by using the automatically created ``pytb`` command)

****************************
Remote Debugger ``pytb rdb``
****************************

A simple command line interface for the remote debugger rdb.
The subcommand expects a function parameter which should be either
``client`` or ``server``.

The ``server`` function exposes a similar interface to the original
``pdb`` command line. Additionally you can specify the interface and port
to bind to and listening for incoming connections as well as the verbosity
of the debug server.

.. code-block:: none

    usage: pytb rdb server [-h] [--host HOST] [--port PORT] [--patch-stdio]
                        [-c commands] [-m]
                        script ...

    positional arguments:
    script         script path or module name to run
    args           additional parameter passed to the script

    optional arguments:
    -h, --help     show this help message and exit
    --host HOST    The interface to bind the socket to
    --port PORT    The port to listen for incoming connections
    --patch-stdio  Redirect stdio streams to the remote client during debugging
    -c commands    commands executed before the script is run
    -m             Load an executable module or package instead of a file

More information on the ``-c`` and ``-m`` parameters can be found in the
`pdb Module Documentation <https://docs.python.org/3/library/pdb.html>`_

The ``client`` function creates a new :class:`pytb.rdb.RdbClient` instance
that connects to the specified host and port.

.. code-block:: none

    usage: pytb rdb client [-h] [--host HOST] [--port PORT]

    optional arguments:
    -h, --help   show this help message and exit
    --host HOST  Remote host where the debug sessino is running
    --port PORT  Remote port to connect to

Both functions fall back to the values provided in the effective
.pytb.conf file (see :class:`pytb.config.Config`) for the ``--host``,
``--port`` and ``--patch-stdio`` parameters

Example usage:

Start a debug server listening on the interface and port read from the
.pytb.conf file. This command does not start script execution until a
client is connected:

.. code-block:: none

    pytb rdb server -c continue myscript.py arg1 arg2 --flag

From another terminal (possibly on another machine) connect to the session.
Since we passed the 'continue' command when starting the server,
the script will be executed until the end or to the first unhandled exception
as soon as the client connects. Without this, script execution would be stopped
before the first line is executed and the client would be presented with
a debug shell.
Because we do not specify a ``--port`` argument, the default port pecified in
the config file is used.

.. code-block:: none

    python -m pytb rdb client --host 192.168.1.15
