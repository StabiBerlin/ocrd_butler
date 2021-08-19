# -*- coding: utf-8 -*-
""" some utility functions
"""


def merge_dicts(A: dict, B: dict) -> dict:
    """ merge dictionaries recursively into a new object. Second dict values
    win conflicts.

    >>> merge_dicts({'a': 1}, {'a': 2, 'b': 3})
    {'a': 2, 'b': 3}

    >>> merge_dicts({1: {1: 2}}, {1: {2: 3}})
    {1: {2: 3, 1: 2}}

    >>> merge_dicts({}, {1: 2})
    {1: 2}

    """
    res = {}
    for key, value in {**B, **A}.items():
        if key in B:
            if type(value) is dict and type(B[key]) is dict:
                res[key] = merge_dicts(value, B[key])
            else:
                res[key] = B[key]
        else:
            res[key] = value
    return res
