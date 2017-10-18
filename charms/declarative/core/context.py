"""Attempt at a largely read-only context.

Essentially, it's a dictionary, but read-only. which is a bit of
a cheat.  After all we have to be able to assign to the thing in
the first place!

note that the  getting allows callables, and just stores them, but
getting them out requires resolving the callable.  By definition
they have to be callable with one parameter that is the context
itself.  (annoying infinite callables possible here...)

dict like objects become attrdicts, and list like objects become tuples

Note also that keys automatically have '-' replaced with '_' so that they can
be accessed 'attr'-like.  e.g. context().one.two.three rather than
context()['one']['two']['three'], although both forms are supported.
"""

import collections
import collections.abc
import json

from utils import (
    maybe_format_key,
    KeyExists,
)

JSON_ENCODE_OPTIONS = dict(
    sort_keys=True,
    allow_nan=False,
    indent=None,
    separators=(',', ':'),
)

__context__ = collections.OrderedDict()


def context(keys=None):
    """The context() is a readonly, lazy, data structure that resolves to
    dictionaries, lists and values.  It uses an OrderedDict() to keep keys
    in order, and when serialized (for comparison purposes only), it sorts the
    keys of dictionaries for consistency.

    If keys is set, and not a string, then it is used to filter the context, to
    provided a restricted set of keys.

    :param keys: if keys is a list or string, then a restricting version of the
        context is returned.
    :returns: read only dictionary-like object
    """
    global __context__
    if keys is None:
        return AttrDict(__context__)
    ctxt = collections.OrderedDict()
    if isinstance(keys, str):
        keys = (str, )
    elif not isinstance(keys, collections.abc.Sequence):
        raise RuntimeError("keys passed to context is not a string or sequence"
                           ": {}".format(keys))
    for key in keys:
        k = maybe_format_key(key)
        try:
            ctxt[k] = __context__[k]
        except KeyError:
            # TODO: log this error?
            pass
    return AttrDict(ctxt)


def key_exists(key):
    """Returns True if the key exists in the context.

    :param key: str
    :returns: boolean
    """
    global __context__
    return maybe_format_key(key) in __context__


def serialize_key(key=None):
    """Serialise to a string the context, and optionally, just a key.

    This method resolves the callables, and serialises the context (or a
    top-level key of it) to a compact string.  This is for comparason purposes,
    as the context is NOT supposed to be serialised to a backing store.

    If there is no context at the key then None is returned

    :param key: OPTIONAL top level string key.
    :returns: JSON string repr of the data in the context, optionally at key
    :raises: KeyError if the key is not found (and not None)
    """
    c = context()
    if key is not None:
        c = c.get(maybe_format_key(key), None)
        if c is None:
            return None
    return ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(c)


def set_context(key, data):
    """Set a top level item to some data.

    The top level is the only way of adding data to the context.  If the key
    already exists, a KeyExists error is returned.

    :param key: str for the key.
    :param data: either a dictionary, list, callable or value
    :raises: KeyExists exception if the key already exists
    """
    global __context__
    key = maybe_format_key(key)
    if key in __context__:
        raise KeyExists("Key '{}' already exists".format(key))
    __context__[key] = _resolve_value(data)


def _resolve_value(value):
    """Turn value into an immutable object (as much as possible).

    If it's a callable (i.e. has a __call__(...) method) then return
    the lazy Callable() instance.
    If it's a dictionary like object, return the ReadOnlyDict() object.
    If it's a list like object, return the ReadOnlyList() object.
    Otherwise, just return the value.  Ultimately, it's supposed to be jsonable
    so this means that it should resolve to strings, dicts, numbers and lists.

    :param value: ANY value.
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
        # self.callable = fn
        # self.called = False
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
            self._attrs['result'] = _resolve_value(_callable)
        return self._attrs['result']

    def __setattr__(self, key, value):
        if key != '_attrs':
            raise TypeError("{} does not allow setting attributes or items"
                            .format(self.__class__.__name__))
        super().__setattr__(key, value)

    __setitem__ = __setattr__

    def __repr__(self):
        if self._attrs['called']:
            s = "lamdba x: {}".format(repr(self._attrs['result']))
        else:
            s = repr(self._attrs['callable'])
        return "Callable({})".format(s)

    def __str__(self):
        if self._attrs['called']:
            return str(self._attrs['result'])
        else:
            return "<not-called-yet>"

    def __serialize__(self):
        v = self()
        try:
            return v.__serialize__()
        except AttributeError:
            return ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(v)


def context_caller_helper(key, f):
    """This helper converts a function f(arg) -> f() where arg is resolved
    dynamically as a call to context().

    The result is set into the context at the key provided.  If the key already
    exists then a KeyExists error is raised when it is attempted to be set
    during the call.

    This is to make it easier to insert callables into the context object

    :param f: function in the form f(arg) -> result
    :returns: function in the form f() -> result
    :raises: AssertionError if 'f' is not callable.
    """
    assert callable(f)
    key = maybe_format_key(key)
    return lambda: set_context(key, f(context()))


def copy(key):
    """Create a late-binding copy function that copies from a name to another
    context.

    Usage would be something like:

    set_context('copy-to', copy('copy-from'))

    As context is read only, we can use a lambda to lazily evaluate the
    context.get() operation and only do it when 'copy-to' is accessed.
    """
    return lambda: context().get(maybe_format_key(key))


class BaseAttrDict(collections.abc.Mapping):
    """Base calls for readonly dictionaries.  Implements the methods of Mapping
    to get a readonly dictionary.  Also supprts repr() and str() to help with
    debugging, and a __serialize__() method to convert to a string for
    comparison purposes.

    Note that it takes a shallow copy of the dictionary, so that changes to the
    original don't affect this copy.
    """

    def __init__(self, data):
        assert isinstance(data, collections.abc.Mapping)
        self._data = data.copy()

    def __getitem__(self, key):
        raise NotImplementedError()

    def __setattr__(self, key, value):
        if key != "_data":
            raise TypeError("{} does not allow setting of attributes"
                            .format(self.__class__.__name__))
        super().__setattr__(key, value)

    __getattr__ = __getitem__

    def __setitem__(self, key, value):
        raise TypeError("{} does not allow setting of items"
                        .format(self.__class__.__name__))

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return ("{}({{{}}})"
                .format(self.__class__.__name__,
                        ", ".join(["{}: {}".format(repr(k), repr(v))
                                   for k, v in self._data.items()])))

    def __str__(self):
        return "{{{}}}".format(", ".join(["{}: {}".format(k, v)
                                          for k, v in self._data.items()]))

    def __serialize__(self):
        """Serialise (to a JSON compact string) the dictionary.  Uses the
        JSON_ENCODE_OPTIONS to determine the format of the string.
        """
        o = collections.OrderedDict()
        for k, v in self._data.items():
            try:
                o[k] = v.__serialize__()
            except AttributeError:
                o[k] = ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(v)
        return o


class AttrDict(BaseAttrDict):
    """The readonly dictionary with key formatting, so that they can be used as
    attributes.
    """

    def __getitem__(self, key):
        return self._data[maybe_format_key(key)]

    __getattr__ = __getitem__


class ReadOnlyDict(BaseAttrDict):
    """The ReadOnly dictionary that handles callables."""

    def __init__(self, data):
        """Initialise the dictionary, by copying the keys, values over to an
        OrderedDict (to preseve the key order), and ensure that the values are
        also read-only.  This recurses till the values are simple values, or
        callables.

        :param data: a dictionary/mapping supporting structure (iter)
        :raises AssertionError: if data is not iterable and mapping
        """
        assert isinstance(data, collections.abc.Mapping)
        self._data = collections.OrderedDict()
        for k, v in data.items():
            self._data[maybe_format_key(k)] = _resolve_value(v)

    def __getitem__(self, key):
        """Gets the item using the key, resolves a callable.

        :param key: string, or indexable object
        :returns: value of item
        """
        value = self._data[maybe_format_key(key)]
        if isinstance(value, Callable):
            value = value()
        return value

    __getattr__ = __getitem__

    def __iter__(self):
        for k, v in self._data.items():
            if isinstance(v, Callable):
                v = v()
            yield k, v


class ReadOnlyList(collections.abc.Sequence):
    """Essentially, this is a 'smart' tuple.  It copies iterable data into a
    tuple, and resolves each value either to a value, a callable, or another
    read-only structure.  The purpose is to make a read-only list.
    """

    def __init__(self, data):
        """Takes data and copies it to an internal tuple which also recursively
        resolves the values to a read-only data structure.

        :param data: must be iterable, so that it can be copied.
        :raises AssertionError: if data can't be sequenced
        """
        assert (isinstance(data, collections.abc.Iterator) and
                not isinstance(data, str))
        self._data = tuple([_resolve_value(v) for v in data])

    def __getitem__(self, index):
        """Gets the item at index, resolving the values as needed"""
        value = self._data[index]
        if isinstance(value, Callable):
            value = value()
        return value

    def __setitem__(self, key, value):
        raise TypeError("{} does not allow setting of items"
                        .format(self.__class__.__name__))

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        for v in self._data:
            if isinstance(v, Callable):
                v = v()
            yield v

    def __repr__(self):
        return ("{}(({}))"
                .format(self.__class__.__name__,
                        ", ".join(["{}".format(repr(v)) for v in self._data])))

    def __str__(self):
        return "({})".format(", ".join(["{}".format(v) for v in self._data]))

    def __serialize__(self):
        o = []
        for v in self._data:
            try:
                o.append(v.__serialize__())
            except AttributeError:
                o.append(ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(v))
        return o


class ContextJSONEncoder(json.JSONEncoder):
    """This is a custom JSONEncoder that knows how to serialise Callable(),
    BaseAttrDict and ReadOnlyList.
    """

    def default(self, o):
        if isinstance(o, (Callable, BaseAttrDict, ReadOnlyList)):
            return o.__serialize__()
        return json.JSONEncoder.decode(self, o)
