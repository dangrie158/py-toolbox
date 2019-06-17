----------------
pytb.core module
----------------

********************************
Autoconfigure toolbox frameworks
********************************

The ``pytb`` package provides an ``init()`` method that allows
to automatically configure certain frameworks from the toolbox.

The behavior of this method is configured based on the values in
:attr:`pytb.config.current_config`.

The method has a parameter ``verbose`` which defaults to ``True``
which enables some output while initializing the subsystems.
If you want to quietly initialize, set `verbose` explicitly to `False`.

To avoid problems with multiple initializations, the method raises a
:class:`RuntimeException` if init is called a second time.

    >>> from pytb.core import init
    >>> init()
    'disable_module_cache' not set, skipping global context
    installing NotebookLoader into 'sys.meta_path'
    installing RDB as default debugger in 'sys.breakpointhook'

*****************
API Documentation
*****************

.. automodule:: pytb.core
    :members:
    :show-inheritance:
