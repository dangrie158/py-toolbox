---------------
pytb.rdb module
---------------

****************
Remote Debugging
****************

Sometimes you do not have a nice way to control the debugger on
the local machine. For example in a jupyter notebook the readline
interface is horrible to use.

The debugger is designed to act as a drop-in replacement for the standard
``pdb`` debugger. However, when starting a debug session (e.g. using
``set_trace()``) the debugger opens a socket and listens on the specified
interface and port for a client.

The client can either be a simple TCP socket tool (like ``netcat``) or
the provided ``RdbClient``.

The debugger can be invoked by calling ``set_trace()``

*****************
API Documentation
*****************

.. automodule:: pytb.rdb
    :members:
    :show-inheritance:
    :exclude-members: Rdb

    .. autoclass:: pytb.rdb.Rdb
        :members: _run_mainsafe
