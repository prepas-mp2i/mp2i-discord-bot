from collections import defaultdict


class DotDict(dict):
    """
    Create a dictionary that supports dot notation
    as well as dictionary access notation.
    """

    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __init__(self, dct: dict):
        super().__init__(dct)
        for key, value in dct.items():
            if isinstance(value, dict):
                value = DotDict(value)
            self[key] = value


class DefaultDotDict(defaultdict, DotDict):
    """
    Create a defaultdict that support DotDict functionalities.
    """

    def __init__(self, default: callable, dct: dict):
        super().__init__(default, dct)

        for key, value in dct.items():
            if isinstance(value, dict):
                value = DefaultDotDict(default, value)
            self[key] = value
