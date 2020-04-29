----------------------
Command Line Interface
----------------------

The toolkit can be run as an executable (e.g. using the ``-m`` switch
of the python command or by using the automatically created ``pytb`` command)

********************************
Task Scheduler ``pytb schedule``
********************************

Command line interface for the
:doc:`schedule module <modules/schedule>`.

Currently only the ``--at`` mode is supported using a cron-like syntax.

The cron-like pattern has the following order: min hour day month weekday.
The following pattern rules are supported:

- ``i`` sequence contains only the element i
- ``*`` indicates that all values possible for this part are included
- ``i,j,k`` specifies a list of possible values
- ``i-j`` specifies a range of values *including* ``j``
- ``i-j/s`` additionally specifies the step-size

For weekday, the values ``0`` and ``7`` both represent sunday.

.. code-block:: none

    usage: pytb schedule [-h] [--at * * * * *] script ...

    positional arguments:
    script          script path or module name to run
    args            additional parameter passed to the script

    optional arguments:
    -h, --help      show this help message and exit
    --at * * * * *  Execute the task each time the cron-like pattern matches

**************************************
Notifications for long running scripts
**************************************

Command line interface for the
:doc:`notification module <modules/notification>`.

You can choose a build-in notifier via the ``via-email`` and
``via-stream`` switches.
Notification rules can be configured via the ``--when-done``,
``--when-stalled`` and ``--every`` options.

.. code-block:: none

    usage: pytb notify [-h] [--every X] [--when-stalled X] [--when-done]
                    {via-email,via-stream} ...

    positional arguments:
    {via-email,via-stream}
                            notifier

    optional arguments:
    -h, --help            show this help message and exit
    --every X             Send a notification every X seconds
    --when-stalled X      Send a notification if the script seems to be stalled
                            for more than X seconds
    --when-done           Send a notification whenever the script finishes

E-Mail Notifier
***************

.. code-block:: none

    usage: pytb notify via-email [-h] [--recipients RECIPIENTS [RECIPIENTS ...]]
                                [--smtp-host SMTP_HOST] [--smtp-port SMTP_PORT]
                                [--sender SENDER] [--use-ssl] [-m]
                                script ...

    positional arguments:
    script                script path or module name to run
    args                  additional parameter passed to the script

    optional arguments:
    -h, --help            show this help message and exit
    --recipients RECIPIENTS [RECIPIENTS ...]
                            Recipient addresses for the notifications
    --smtp-host SMTP_HOST
                            Address of the external SMTP Server used to send
                            notifications via E-Mail
    --smtp-port SMTP_PORT
                            Port the external SMTP Server listens for incoming
                            connections
    --sender SENDER       Sender Address for notifications
    --use-ssl             Use a SSL connection to communicate with the SMTP
                            server
    -m                    Load an executable module or package instead of a file

**Note**: If you want to specify multiple recipients as the last option
in your command line, use ``--`` to seperate the argument list from the
script option with multiple arguments.

*Example*:

.. code-block:: none

    pytb notify --when-done --when-stalled 5 via-email --recipients recipient1@mail.com recipient2@mail.com -- myscript.py param1 --param2=val 

Stream Notifier
***************

.. code-block:: none

    usage: pytb notify via-stream [-h] [--stream STREAM] [-m] script ...

    positional arguments:
    script           script path or module name to run
    args             additional parameter passed to the script

    optional arguments:
    -h, --help       show this help message and exit
    --stream STREAM  The writable stream. This can be a filepath or the special
                    values `<stdout>` or `<stderr>`
    -m               Load an executable module or package instead of a file

**Note**: If you want to use the ``stdout`` or ``stderr`` stream as output,
simply use the constants ``<stdout>`` or ``<stderr>`` for the stream parameter.
If your shell tries to replace those values (e.g. ``zsh``), quote the strings.

*Example*:

.. code-block:: none

    python -m pytb notify --every 5 via-stream --stream="<stdout>" -m http.server

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
