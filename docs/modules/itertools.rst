---------------------
pytb.itertools module
---------------------

************************************************************
Flexibly test a number possible configurations of a function
************************************************************

Assume you have a function that takes a number of parameters:

    >>> def my_func(a, b, c=2, **kwargs):
    ...    print(' '.join((a, b, c)), kwargs)

And you want to call it with multiple parameter combinations

    >>> my_params = {
    ...     'a': 'a1',
    ...     'b': ('b1','b2'),
    ...     'c': ('c1', 'c2'),
    ...     'additional_arg': 'val'
    ... }

You can use the :meth:`named_tuple` function of this module to create any
possible combination of the provided parameters

    >>> for params in named_product(my_params):
    ...     my_func(**params)
    a1 b1 c1 {'additional_arg': 'val'}
    a1 b1 c2 {'additional_arg': 'val'}
    a1 b2 c1 {'additional_arg': 'val'}
    a1 b2 c2 {'additional_arg': 'val'}

Excluding some combinations
---------------------------

If some parameter combinations are not allowed, you can use the
functions ability to work with nested dicts to overwrite values defined in
an outer dict

    >>> my_params = {
    ...     'a': 'a1',
    ...     'b': ('b1','b2'),
    ...     'c': {
    ...         'c1': {'b': 'b1'},
    ...         'c2': {},
    ...         'c3': {
    ...             'additional_arg': 'other val',
    ...             'another arg': 'yet another val'}
    ...     },
    ...     'additional_arg': 'val'
    ... }

    >>> for params in named_product(my_params):
    ...     my_func(**params)
    a1 b1 c1 {'additional_arg': 'val'}
    a1 b1 c2 {'additional_arg': 'val'}
    a1 b2 c2 {'additional_arg': 'val'}
    a1 b1 c3 {'additional_arg': 'other val', 'another arg': 'yet another val'}
    a1 b2 c3 {'additional_arg': 'other val', 'another arg': 'yet another val'}

Note that for ``c='c1'`` only ``b='b1'`` was used. You can also define
new variables inside each dict that only get used for combinations in
this branch.

``safe_copy`` of values
-----------------------

By default, all values are (deep) copied before they are yielded from the
generator. This is really useful, as otherwise any change you make to an
object in any combination would change the object for all other combination.

If you have large objects in your combinations however, copying may be
expensive. In this case you can use the ``safe_copy`` parameter to control
*if* and *which* objects should be copied before yielding.

*****************
API Documentation
*****************

.. automodule:: pytb.itertools
    :members:
    :show-inheritance:
