--------------
pytb.io module
--------------

**************************
Redirecting output streams
**************************

The ``io`` Module offers function to temporarly redirect or mirror
``stdout`` and ``stderr`` streams to a file

Stream redirection:

    >>> from pytb.io import redirected_stdout
    >>> with redirected_stdout('stdout.txt'):
    ...     print('this will be written to stdout.txt and not to the console')

Stream mirroring
****************

    >>> from pytb.io import mirrored_stdstreams
    >>> with mirrored_stdstreams('alloutput.txt'):
    ...     print('this will be written to alloutput.txt AND to the console')

*****************
API Documentation
*****************

.. automodule:: pytb.io
    :members:
    :show-inheritance:
