"""Declarative helpers, e.g. mapping 'making statements' to actually putting
things in the context
"""

import yaml

from charmhelpers.core import hookenv

import reactor
from utils import maybe_format_key


def config():
    reactor.add_input('config', hookenv.config)


def hooks(current_hook):
    # process all the names of the hooks we have and add them to the context as
    # 'hook.{name}'.  Only the one which is present will be set to True
    pass


def _add_hook(hook_name, state):
    reactor.add_input("hook.{}".format(maybe_format_key(hook_name)), state)


def relation(name, schema):
    # in theory, schema is a json schema (as a python dict) used to validate
    # the data on a relation.
    pass


def charmhelpers_context(name, ctxt):
    # Note, this is really inefficient.  We actually want to compute them based
    # on a hook firing.  In fact, why not have a context that is the hook ->
    # True?
    reactor.add_input(name, ctxt)


# need to consider the model to use to write a config file and restart
# services. We want to be able to declare our intentions as:
# service -> files -> contexts
