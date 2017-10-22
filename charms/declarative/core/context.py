"""This is a read only 'context' implementation for the reactor

Essentially, it's a dictionary, but read-only. which is a bit of
a cheat.  After all we have to be able to assign to the thing in
the first place!

Note that the context allows 'callables', and just stores them, but
getting them out requires resolving the callable.

Dict like objects become attrdicts, and list like objects become tuples

Note also that keys automatically have '-' replaced with '_' so that they can
be accessed 'attr'-like.  e.g. context().one.two.three rather than
context()['one']['two']['three'], although both forms are supported.
"""

import collections
import collections.abc

from utils import (
    maybe_format_key,
)

from ro_types import (
    resolve_value,
    ContextJSONEncoder,
    ReadOnlyDict,
    ReadOnlyWrapperDict,
)


from exceptions import (
    KeyExists,
)

# the global context is held here
__context__ = collections.OrderedDict()


def context(keys=None, _context=None):
    """The context() is a readonly, lazy, data structure that resolves to
    dictionaries, lists and values.  It uses an OrderedDict() to keep keys
    in order, and when serialized (for comparison purposes only), it sorts the
    keys of dictionaries for consistency.

    If keys is set, and not a string, then it is used to filter the context, to
    provided a restricted set of keys.

    :param keys: if keys is a list or string, then a restricting version of the
        context is returned.
    :param _context: the context to work with; defaults to the global
        __context__
    :returns: read only dictionary-like object
    :raises: AttributeError if the keys are not valid identifiers
    """
    if _context is None:
        global __context__
        _context = __context__
    if keys is None:
        return ReadOnlyWrapperDict(_context)
    ctxt = collections.OrderedDict()
    if isinstance(keys, str):
        keys = (str, )
    elif not isinstance(keys, collections.abc.Sequence):
        raise RuntimeError("keys passed to context is not a string or sequence"
                           ": {}".format(keys))
    for key in keys:
        k = maybe_format_key(key)
        try:
            ctxt[k] = _context[k]
        except KeyError:
            # TODO: log this error?
            pass
    return ReadOnlyWrapperDict(ctxt)


def key_exists(key, _context=None):
    """Returns True if the key exists in the context.

    :param key: str
    :param _context: the context to work with; defaults to the global
        __context__
    :returns: boolean
    """
    if _context is None:
        global __context__
        _context = __context__
    return maybe_format_key(key) in _context


def serialize_key(key=None, _context=None):
    """Serialise to a string the context, and optionally, just a key.

    This method resolves the callables, and serialises the context (or a
    top-level key of it) to a compact string.  This is for comparason purposes,
    as the context is NOT supposed to be serialised to a backing store.

    If there is no context at the key then None is returned

    :param key: OPTIONAL top level string key.
    :param _context: the context to work with; defaults to the global
        __context__
    :returns: JSON string repr of the data in the context, optionally at key
    :raises: KeyError if the key is not found (and not None)
    """
    if _context is None:
        global __context__
        _context = __context__
    c = context(_context=_context)
    if key is not None:
        c = c.get(maybe_format_key(key), None)
        if c is None:
            return None
    return ContextJSONEncoder(**JSON_ENCODE_OPTIONS).encode(c)


def set_context(key, data, _context=None):
    """Set a top level item to some data.

    The top level is the only way of adding data to the context.  If the key
    already exists, a KeyExists error is returned.

    :param key: str for the key.
    :param data: either a dictionary, list, callable or value
    :param _context: the context to work with; defaults to the global
        __context__
    :raises: KeyExists exception if the key already exists
    """
    if _context is None:
        global __context__
        _context = __context__
    key = maybe_format_key(key)
    if key in _context:
        raise KeyExists("Key '{}' already exists".format(key))
    _context[key] = resolve_value(data)


def context_caller_helper(key, f, _context=None):
    """This helper converts a function f(arg) -> f() where arg is resolved
    dynamically as a call to context().

    The result is set into the context at the key provided.  If the key already
    exists then a KeyExists error is raised when it is attempted to be set
    during the call.

    This is to make it easier to insert callables into the context object

    :param key: str for the key.
    :param f: function in the form f(arg) -> result
    :param _context: the context to work with; defaults to the global
        __context__
    :returns: function in the form f() -> result
    :raises: AssertionError if 'f' is not callable.
    """
    if _context is None:
        global __context__
        _context = __context__
    assert callable(f)
    key = maybe_format_key(key)
    return lambda: set_context(key, f(context(_context=_context)))


def copy(key, _context=None):
    """Create a late-binding copy function that copies from a name to another
    context.

    Usage would be something like:

    set_context('copy-to', copy('copy-from'))

    As context is read only, we can use a lambda to lazily evaluate the
    context.get() operation and only do it when 'copy-to' is accessed.

    :param key: str for the key.
    :param _context: the context to work with; defaults to the global
        __context__
    :returns: F() -> copied context entry
    """
    if _context is None:
        global __context__
        _context = __context__
    return lambda: context(_context=_context).get(maybe_format_key(key))
