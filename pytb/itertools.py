"""
Methods to work with iterables conveniently.
(methods that could be in the python stdlib itertools package)
"""

import itertools
from collections.abc import Iterable
from typing import Optional, Any, Mapping, Generator


def named_product(
    values: Optional[Mapping[Any, Any]] = None,
    repeat: int = 1,
    **kwargs: Mapping[Any, Any]
) -> Generator[Any, None, None]:
    r"""
    .. testsetup:: *

        from pytb.itertools import named_product

    Return each possible combination of the input parameters (cartesian product),
    thus this provides the same basic functionality of :meth:``itertools.product``.
    However this method provides more flexibility as it:

    1. returns dicts instead of tuples

    .. doctest::

        >>> list(named_product(a=('X', 'Y'), b=(1, 2)))
        [{'a': 'X', 'b': 1}, {'a': 'X', 'b': 2}, {'a': 'Y', 'b': 1}, {'a': 'Y', 'b': 2}]

    2. accepts either a dict or kwargs

    .. doctest::

        >>> list(named_product({ 'a':('X', 'Y') }, b=(1, 2)))
        [{'a': 'X', 'b': 1}, {'a': 'X', 'b': 2}, {'a': 'Y', 'b': 1}, {'a': 'Y', 'b': 2}]

    3. accepts nested dicts

    .. doctest::

        >>> list(named_product(
        ...     a=(
        ...             {'X': {'b':(1,2)}},
        ...             {'Y': {
        ...                     'b': (3, 4),
        ...                     'c': (5, )
        ...                   }
        ...             }
        ...     )
        ... ))
        [{'a': {'X': {'b': (1, 2)}}}, {'a': {'Y': {'b': (3, 4), 'c': (5,)}}}]

    4. accepts scalar values

    .. doctest::

        >>> list(named_product(b='Xy', c=('a', 'b')))
        [{'b': 'Xy', 'c': 'a'}, {'b': 'Xy', 'c': 'b'}]

    :param values: a dict of iterables used to create the cartesian product
    :param repeat: repeat iteration of the product N-times
    :param \**kwargs: optional keyword arguments. The dict of
        keyword arguments is merged with the values dict,
        with ``kwargs`` overwriting values in ``values``
    """
    # merge the values dict with the kwargs, giving
    # precedence to the kwargs
    if values is not None:
        kwargs = {**values, **kwargs}

    # convert scalar values to 1-tuples
    for name, entry in kwargs.copy().items():
        # always pack strings as they are iterable,
        # but most likely used as scalars
        if isinstance(entry, str):
            kwargs.update({name: (entry,)})
        elif not isinstance(entry, Iterable):
            # pack the value into a tuple
            kwargs.update({name: (entry,)})

    if any(isinstance(v, dict) for v in kwargs.values()):
        # recursivley expand all dict elements to the set of values
        for key_outer, val_outer in kwargs.items():
            if isinstance(val_outer, dict):
                for key_inner, val_inner in val_outer.items():
                    subproduct = {key_outer: key_inner, **val_inner}
                    # yield from to exhaust the recursive call to the iterator
                    yield from named_product(repeat=repeat, **{**kwargs, **subproduct})
    else:
        # non-recursive exit point yields the product of all values
        for combination in itertools.product(*kwargs.values(), repeat=repeat):
            yield dict(zip(list(kwargs.keys()), combination))
