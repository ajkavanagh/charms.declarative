import collections
import collections.abc
import json

from charms.declarative.core.utils import maybe_format_key

JSON_ENCODE_OPTIONS = dict(
    sort_keys=True,
    allow_nan=False,
    indent=None,
    separators=(',', ':'),
)


def resolve_value(value):
    """Turn value into an immutable object (as much as possible).

    If it's a callable (i.e. has a __call__(...) method) then return
    the lazy Callable() instance.
    If it's a dictionary like object, return the ReadOnlyDict() object.
    If it's a list like object, return the ReadOnlyList() object.
    Otherwise, just return the value.  Ultimately, it's supposed to be jsonable
    so this means that it should resolve to strings, dicts, numbers and lists.

    :param value: ANY value.
    :param _callable: the callable to use to resolve the types
    :returns: transformed/wrapped value for 'read-only' use.
    """
    if callable(value):
        return Callable(value)
    if isinstance(value, collections.abc.Mapping):
        return ReadOnlyDict(value)
    elif (not isinstance(value, str) and
          isinstance(value, collections.abc.Sequence)):
        return ReadOnlyList(value)
    return value


def maybe_resolve_callable(v):
    """Return v if it's not a Callable, else call the value to resolve it.

    :param v: maybe a Callable
    :returns: v or v() if v isinstance(Callable)
    :raises: Exception if the call raises an exception
    """
    if isinstance(v, Callable):
        return v()
    return v


class Callable():
    """The Callable() class contains a lazy-evaluated callable function that
    has the signature:

    def callable() -> value

    Note that callables can be nested, although they will ALL be resolved to a
    value (that could be a dictionary with other callables) when they are
    called.

    essentially:

    >>> y = lambda: 2
    >>> x = Callable(lambda : y() + 1)
    >>> x()
    >>> 3
    >>> x()
    >>> 3

    The purpose is to be able to embed a read-only callable into the read-only
    data structures.  Thus Callable() has controlled interior mutability that
    resolves ONCE when it is first called, and then caches the result for
    subsequent calls.
    """

    def __init__(self, fn):
        """Initialise the callable with a function.

        The function signature should be no arguments, and this is enforced in
        the __call__()

        :param fn: a function: lambda x: y
        :raises AssertionError: if fn is not callable
        """
        assert callable(fn)
        self._attrs = {
            'callable': fn,
            'called': False,
            'result': None,
        }

    def __call__(self):
        """Return the result of the function, when called with 'c'

        Note, that this memoises the result, so only the 'first' call actually
        counts.
        If the function returns a callable, this is also called until there is
        a result.

        :returns: result of callable, possibly cached.
        :raises: may raise whatever the callable raises.
        """
        if not self._attrs['called']:
            self._attrs['called'] = True
            _callable = self._attrs['callable']
            while True:
                _callable = _callable()
                if not callable(_callable):
                    break
            self._attrs['result'] = resolve_value(_callable)
        return self._attrs['result']

    def __setattr__(self, key, value):
        if key != '_attrs':
            raise TypeError("{} does not allow setting attributes or items"
                            .format(self.__class__.__name__))
        super().__setattr__(key, value)

    __setitem__ = __setattr__

    def __repr__(self):
        if self._attrs['called']:
            s = "lambda: {}".format(repr(self._attrs['result']))
        else:
            s = repr(self._attrs['callable'])
        return "Callable({})".format(s)

    def __str__(self):
        if self._attrs['called']:
            return str(self._attrs['result'])
        else:
            return "<{}>".format(self.__repr__())

    def __serialize__(self):
        v = self()
        return ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(v)


class ReadOnlyWrapperDict(collections.abc.Mapping):
    """A class to wrap an existing dict and make it readonly.  i.e. does not
    copy the keys, but just holds a reference to the original dict

    It also needs to resolve a callable into the called version.
    """

    def __init__(self, data):
        assert isinstance(data, collections.abc.Mapping)
        self.__data__ = collections.OrderedDict()
        for k, v in data.items():
            self.__data__[k] = v

    def __getitem__(self, key):
        if key not in self.__data__:
            raise KeyError("Item '{}' doesn't exist".format(key))
        return maybe_resolve_callable(self.__data__[key])

    def __getattr__(self, key):
        if key in self.__data__:
            return maybe_resolve_callable(self.__data__[key])
        return super().__getattr__(key)

    def __setattr__(self, key, value):
        if key == '__data__':
            super().__setattr__(key, value)
            return
        raise TypeError("{} does not allow setting of attributes"
                        .format(self.__class__.__name__))

    def __setitem__(self, key, value):
        raise TypeError("{} does not allow setting of items"
                        .format(self.__class__.__name__))

    def __len__(self):
        return len(self.__data__)

    def __iter__(self):
        return iter(self.__data__)

    def __repr__(self):
        return ("{}({{{}}})"
                .format(self.__class__.__name__,
                        ", ".join(["{}: {}".format(repr(k), repr(v))
                                   for k, v in self.__data__.items()])))

    def __str__(self):
        return "{{{}}}".format(", ".join(["{}: {}".format(repr(k), v)
                                          for k, v in self.__data__.items()]))

    def __serialize__(self):
        """Serialise ourself (the OrderedDict) to a regular dictionary, which
        the default JSON encoder can use.
        """
        return {k: maybe_resolve_callable(v) for k, v in self.__data__.items()}


class ReadOnlyDict(collections.OrderedDict):
    """The ReadOnly dictionary that handles callables, and preserves order."""

    def __init__(self, data):
        """Initialise the dictionary, by copying the keys and values.  This
        recurses till the values are simple values, or callables.

        :param data: a dictionary/mapping supporting structure (iter)
        :raises AssertionError: if data is not iterable and mapping
        """
        assert isinstance(data, collections.abc.Mapping)
        for k, v in data.items():
            super().__setitem__(maybe_format_key(k), resolve_value(v))

    def __getitem__(self, key):
        """Gets the item using the key, resolves a callable.

        :param key: string, or indexable object
        :returns: value of item
        """
        return maybe_resolve_callable(
            super().__getitem__(maybe_format_key(key)))

    __getattr__ = __getitem__

    def __setattr__(self, key, value):
        raise TypeError("{} does not allow setting of attributes"
                        .format(self.__class__.__name__))

    def __setitem__(self, key, value):
        raise TypeError("{} does not allow setting of items"
                        .format(self.__class__.__name__))

    def __iter__(self):
        for k, v in self.items():
            yield k, maybe_resolve_callable(v)

    def __serialize__(self):
        """Serialise ourself (the OrderedDict) to a regular dictionary, which
        the default JSON encoder can use.
        """
        return {k: v for k, v in self.items()}


class ReadOnlyList(tuple):
    """Essentially, this is a 'smart' tuple.  It copies iterable data into a
    tuple, and resolves each value either to a value, a callable, or another
    read-only structure.  The purpose is to make a read-only list.
    """

    def __new__(cls, data):
        """Takes data and copies it to an internal tuple which also recursively
        resolves the values to a read-only data structure.

        :param data: must be iterable, so that it can be copied.
        """
        return tuple.__new__(cls, [resolve_value(v) for v in data])

    def __getitem__(self, index):
        """Gets the item at index, resolving the values as needed"""
        return maybe_resolve_callable(super().__getitem__(index))

    def __setattr__(self, key, value):
        raise TypeError("{} does not allow setting of items"
                        .format(self.__class__.__name__))

    def __iter__(self):
        for v in super().__iter__():
            yield maybe_resolve_callable(v)

    def __repr__(self):
        return ("{}(({}))"
                .format(self.__class__.__name__,
                        ", ".join(["{}".format(repr(v)) for v in self])))

    def __str__(self):
        return "({})".format(", ".join(["{}".format(v) for v in self]))

    def __serialize__(self):
        return [v for v in self]


class ContextJSONEncoder(json.JSONEncoder):
    """This is a custom JSONEncoder that knows how to serialise Callable(),
    BaseAttrDict and ReadOnlyList.
    """
    # Note the "pragma: no cover" is due to the line being currently impossible
    # to reach as the classes all conspire to ensure there is no default that
    # can be called!  The line is in for insurance, if the implementation is
    # changed.

    def default(self, o):
        if isinstance(o, (Callable, ReadOnlyDict, ReadOnlyList,
                          ReadOnlyWrapperDict)):
            return o.__serialize__()
        return json.JSONEncoder.default(self, o)  # pragma: no cover
