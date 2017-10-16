"""The reactor module which ties together the context and the reactor_core.

This essentially provides the glue between the reactor functions setting values
on the context, and for detecting the context has changed.
"""

import hashlib

import charmhelpers.core.unitdata as unitdata

import context
from utils import maybe_format_key
import reactor_core


# Just reflect the various functions to the reactor core
add_input = reactor_core.add_input
add_compute = reactor_core.add_compute
key_exists = reactor_core.key_exists


def has_key_changed(key):
    """See if the key has changed since the last time to kv() store was
    accessed.

    :param key: string
    :returns: boolean, True if changed
    """
    return _has_key_changed(key, unitdata.kv(), context)


def _has_key_changed(key, _kv, _context):
    """Internal testable has_key_changed function.

    Uses hash_str() function (local) to hash the data in a key and determine
    whether it changed since the kv was last updated.  Note that this is only
    done ONCE per charm hook invocation.

    The _context must have a `serialize_key()` function to provide a string
    representation of the value for hashing.

    :param key: string
    :param _kv: the kev:value store, used to store the changes.
    :oaram _context: the context (dict like object) that the key lives in
    :returns: boolean, True if changed.
    """
    # Note that other parts of the framework are responsible for flushing the
    # keys to the storage system
    key = maybe_format_key(key)
    current = context.serialize_key(key)
    formatted_key = "charms.declarative.context.{}".format(key)
    old_hash = _kv.get(formatted_key, default=None)
    new_hash = hash_str(current)
    changed = (new_hash == old_hash)
    if new_hash is not None:
        _kv.set(formatted_key, new_hash)
    elif old_hash is not None:
        # essentially remove the old value if the new_hash is None, but the
        # old_hash wasn't.  Keeps things consistent
        _kv.unset(formatted_key)
    return changed


def hash_str(s, hash_type='md5'):
    """Hash the string using the default md5 hash function.  If the string is
    actually a None, then just return None.

    :param s: string to hash
    :hash_type: default 'md5', but any hash function from the hashlib
    :returns: the hashed string
    """
    if s is None:
        return None
    h = getattr(hashlib, hash_type)()
    h.update(str(s))
    return h.hexdigest()


def run():
    """Run the reactor, using the default reactor_core.__reactor__ and the
    has_key_changed function, which uses the unitdata.kv() store.

    :raises AbortExecution: if the handler functions fail.  This should be
        treated as a hard abort of the hook function, and not persist to the
        kb() store.
    """
    reactor_core.run(has_key_changed, context.context, context.set_context)
