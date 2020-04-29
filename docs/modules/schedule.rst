---------------------
pytb.schedule module
---------------------

**************************************************************
Run commands on certain dates with a cron-like date expression
**************************************************************

You can use the :func:`at` and :func:`every` as a decorator for
to turn that function into a scheduled thread object.
Use the :meth:`start_schedule` start the scheduled execution.

You can use the :meth:`stop` to stop any further scheduling.
The decorated function is also still directly callable to
execute the task in the calling thread.

*****************
API Documentation
*****************

.. automodule:: pytb.schedule
    :members:
    :show-inheritance:
