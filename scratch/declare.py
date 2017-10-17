# attempt at writing some of the declarative helpers and tie them into the
# context and the reactor.  This is a bit of a first attempt.
# Note files here needs tests before going into the library.


import collections
import os
import json
import yaml

from charmhelpers.core import hookenv

import reactor


def config():
    """Load the config into the context at the 'config' location
    If it's already loaded, just exit
    """
    if reactor.key_exists('config'):
        return
    # lazily load the config when it is asked for -- which will be soon.
    # and load it into the reactor at the 'context' location
    reactor.add_input('config', lambda: hookenv.config())


# store the possible schema files against interfaces
__schema_file_map__ = {}
SchemaMap = collections.namedtuple('SchemaMap',
                                   'interface schema_data persistence')


def interface_schema(name, schema_file=None, persistent=True):
    """Declare an interface schema that will be used when pulling in the
    interface data.  Nothing happens until the interface is queried.
    This just creates an association to intepret the data on the interface.

    Schema files live in the 'schemas' sub-directory of the charm.  By default,
    they are the same name as the interface, but a custom one can be overridden
    using the schema_file param.

    :param name: the interface name to associate a schema with
    :param schema_file: (default None) a yaml schema file to associate with
        the interface
    :param persistence: (default True) whether to remember what the interface
        was during the last successful invocation of the hook.
    """
    global __schema_file_map__
    if name in __schema_file_map__:
        raise reactor.KeyExists(
            "schema file for interface '{}' already exists.".format(name))
    # check that the file actually exists
    if schema_file:
        file = os.path.join(hookenv.charm_dir(), 'schemas', schema_file)
        if not os.path.isfile(file):
            raise IOError("File {} is missing".format(file))
    else:
        # try the json version
        file = os.path.join(hookenv.charm_dir(), 'schemas',
                            '{}.yaml'.format(name))
        if not os.path.isfile(file):
            raise Exception("Interface '{}' has no schema associated."
                            .format(name))
    # now try to load the yaml schema
    with open(file) as fp:
        schema_data = yaml.safe_load(fp)
    __schema_file_map__[name] = SchemaMap(name,
                                          schema_data,
                                          not(not(persistent)))


def variable(name, value_or_callable, persistent=True):
    """Declare a variable, also known as an input, from a value or variable.
    The persistence is whether it was stored last time, (true/false), the
    predicates are evaluated to determine whether to actually set the variable
    or not.

    :param name: the name of the variable (goes on context/reactor)
    :param value_or_callable: the value of the variable
    :persistence: whether to check the previous version of the variable
    """
    reactor.add_input(name, value_or_callable, persistent)


# create an alias for 'var'
var = variable


def function(name, function, dependencies, persistent=True, predicates=None):
    """Declare a function that is run if any of the dependencies has changed,
    and all of the predicates evaluate to True.  Persistent, if false, means
    that the function's output is never saved, and thus is always 'new' and
    will always trigger any dependent functions.

    The predicates are callables that are resolved ONLY if the function is
    triggered.

    :param name: the name of the reactor item
    :param function: the callable that will be called if any dependency
        triggers it, AND all predicates, if present, are True
    :param dependencies: list of strings, naming the dependent cells.
    :param persistent: if False, then the output is not persisted, and the cell
        always changes.
    :param predicates: list of callables that has to be all(True) for the
        function to be called.

    NOTE: we could model the predicates as a wrapper function around the other
    function, or instead, add a dependency function that are the predicates
    that then only feeds into the desired function, and wrap the function if
    that is True?

    TODO: actually predicates needs to be baked into the reactor, along with
    short-circuit exceptions AbortFunction() and AbortExecution() to drop out
    of the system altogether.

    NOTE: how to synchronise multiple changes so that functions get called
    after everyone else is done?
    """
    # HERE - work out what we need to do next!
    pass


# declare.function('name', callable, [dependencies], persistent=True,
                 # predicates=None)

