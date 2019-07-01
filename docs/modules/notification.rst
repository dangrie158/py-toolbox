------------------------
pytb.notification module
------------------------

********************************************
Setup monitoring for your long running tasks
********************************************

Automatic task progress and monitoring notification via E-Mail.
Especially useful to supervise long-running code blocks.

Concrete Notifier implementations
*********************************

The base :class:`Notify` class is an abstract class that implements
the general notification management. However, it does not define how
notifications are delivered.

The Framework implements different derived classes with a concrete
implementation of the abstract :meth:`Notify._send_notification()`
method:

:class:`NotifyViaEmail`
    Send notifications as emails using an external SMTP server.

:class:`NotifyViaStream`
    Write notifications as string to a stream.
    The stream can be any writable object (e.g. a TCP or UNIX socket
    or a `io.StringIO` instance). When using pythons `socket <https://docs.python.org/3/library/socket.html#module-socket>`_
    module, use the sockets :meth:`makefile` method to get a writable stream.

Manually sending Notifications
******************************

You can send Notification manually using the :meth:`now()` method:

.. testsetup::

    from pytb.notification import NotifyViaStream
    import time
    import io

.. doctest::

    >>> stream = io.StringIO()
    >>> notify = NotifyViaStream("testtask", stream)
    >>> # set a custom template used to stringify the notifications
    >>> notify.notification_template = "{task} {reason} {exinfo}"
    >>> notify.now("test successful")
    >>> stream.getvalue()
    'testtask test successful '

Notify when a code block exits (on success or failure)
******************************************************

The :meth:`when_done` method can be used to be notified when a code block
exits. This method will always send exactly one notification when the task
exits (gracefully or when a unhandeled exception is thrown) except if the
``only_if_error`` parameter is ``True``. In this case a graceful exit will
not send any notification.

.. doctest::

    >>> _ = stream.truncate(0)
    >>> _ = stream.seek(0)
    >>> with notify.when_done():
    ...     # potentially long-running process
    ...     pass
    >>> stream.getvalue()
    'testtask done '

When an exception occurs, the ``{exinfo}`` placeholder is populated
with the exception message. The exception is reraised after the notification
is sent and the context exited.

.. doctest::

    >>> _ = stream.seek(0)
    >>> with notify.when_done():
    ...     raise Exception("ungraceful exit occurred")
    Traceback (most recent call last):
        ...
    Exception: ungraceful exit occurred

    >>> stream.getvalue()
    'testtask failed ungraceful exit occurred'

Periodic Notifications on the Progress of long-running Tasks
************************************************************

The :meth:`every` method can be used to send out periodic notifications
about a tasks progress. If the ``incremental_output`` parameter is ``True``
only the newly generated output since the last notification is populated
into the ``{output}`` placeholder.

.. doctest::

    >>> _ = stream.seek(0)
    >>> notify.notification_template = "{task} {reason} {output}\n"

    >>> with notify.every(0.1, incremental_output=True):
    ...     time.sleep(0.12)
    ...     print("produced output")
    ...     time.sleep(0.22)
    >>> print(stream.getvalue().strip())
    testtask progress update <No output produced>
    testtask progress update produced output
    testtask progress update <No output produced>
    testtask done produced output

Notify about stalled code blocks
********************************

Often you want to be notified if your long-running task may have stalled.
The :meth:`when_stalled` method tries to detect a stall and sends out a
notification.

A stall is detected by checking the output produced by the code block.
If for a specified ``timeout`` no new output is produced, the code is
considered to be stalled.
If a stall was detected, any produced output will send another notification
to inform about the continuation.

.. doctest::

    >>> _ = stream.truncate(0)
    >>> _ = stream.seek(0)
    >>> notify.notification_template = "{task} {reason}\n"

    >>> with notify.when_stalled(timeout=0.1):
    ...     time.sleep(0.2)
    ...     print("produced output")
    ...     time.sleep(0.1)
    >>> print(stream.getvalue().strip())
    testtask probably stalled
    testtask no longer stalled

Notify after any iteration over an Iterable
*******************************************

Simply wrap any :class:`Iterable` in :meth:`Notify.on_iteration_of` to get
notified after each step of the iteration has finished.

.. doctest::

    >>> _ = stream.truncate(0)
    >>> _ = stream.seek(0)
    >>> notify.notification_template = "{reason}\n"

    >>> for x in notify.on_iteration_of(range(5), after_every=2):
    ...     pass
    >>> print(stream.getvalue().strip())
    Iteration 2/5 done
    Iteration 4/5 done
    Iteration 5/5 done

**Note**: Because of `how generators work in python <https://stackoverflow.com/questions/44598548/catch-exception-thrown-in-generator-caller-in-python>`_
, it is not possible to handle exceptions that are raised in the loop body.
If you want to get notified about errors that occurred during the loop
execution, you need to wrap the whole loop into a :meth:`when_done` context
with the ``only_if_error`` flag set to ``True``.

.. doctest::

    >>> _ = stream.truncate(0)
    >>> _ = stream.seek(0)
    >>> notify.notification_template = "{reason}\n"

    >>> for x in notify.on_iteration_of(range(5)):
    ...     if x == 1:
    ...         raise Exception("no notification for this :(")
    Traceback (most recent call last):
        ...
    Exception: no notification for this :(

    >>> print(stream.getvalue().strip())
    Iteration 1/5 done

*****************
API Documentation
*****************

.. automodule:: pytb.notification
    :members:
    :show-inheritance:
