"""The basic reactor module.

This has 'input' cells and compute cells, which are string names that are
(nominally) mapped to the context module.

The idea is that the compute cells take a context object, but also have
predicates that are evalutated in an "or" fashion until either all of them are
false, or one of them is true.  If this is the case, then the associated
function is called with the context function passed to the reactor.

The predicates are all just functions that resolve to a boolean.  The compute
functions are are functions that don't take a parameter . (i.e. they should be
'pre-loaded' as required.

Any reactor function that has been executed is then excluded during the
iterative resolution round until NO functions are left that resolve to true.

Note, that an briding module is used to provide the functions that wrap reactor
functions to supply the context and also to update the context as needed from
return values.

Note that reactor functions are referenced by string, ostensibly identical to
the context strings.  This is deliberate.
"""

import collections
import enum

from utils import (
    maybe_format_key,
    KeyExists,
)

__reactor__ = collections.OrderedDict()


Reactor = collections.namedtuple('Reactor',
                                 'type_, name, function, dependents, '
                                 'dependencies')
Type = enum.Enum('Type', 'INPUT COMPUTE')


def add_input(name):
    """Add an input cell to the reactor, with the function 'function'."""
    global __reactor__
    name = maybe_format_key(name)
    if name in __reactor__.keys():
        raise KeyExists("The reactor function '{}' already exists"
                        .format(name))
    # assert callable(function), "Param function must be callable"
    __reactor__[name] = Reactor(Type.INPUT, name, None, set(), [])


def add_compute(name, function, dependencies):
    """Add a compute cell with dependencies.  Note that they don't actually
    have to exist; this will be checked when the 'run()' function is invoked
    which will do a consistency check on the reactor core before proceeding.
    """
    global __reactor__
    name = maybe_format_key(name)
    if name in __reactor__ and __reactor__[name].function is not None:
        raise KeyExists("The reactor function '{}' already exists"
                        .format(name))
    assert callable(function), "Param function must be callable"
    dependencies = [maybe_format_key(d) for d in dependencies]
    # look for a simple circular dependency
    if name in dependencies:
        raise KeyExists(
            "The key '{}' already exists as a compute/input function"
            .format(name))
    if name not in __reactor__:
        __reactor__[name] = Reactor(
            Type.COMPUTE, name, function, set(), dependencies)
    else:
        __reactor__[name] = Reactor(
            Type.COMPUTE, name, function,
            __reactor__[name].dependents, dependencies)
    # Now push the dependencies into existing cells to build the graph
    for d in dependencies:
        if d not in __reactor__:
            __reactor__[d] = Reactor(None, name, None, set(), None)
        __reactor__[d].dependents.add(name)


def _check_reactor():
    # return a boolean to indicate whether it is valid.
    # check that all the computes have functions.
    errors = []
    global __reactor__
    for name, reactor in __reactor__.items():
        if reactor.function is None:
            errors.append("Cell '{}: {}' has no function"
                          .format(name, reactor))
        for d in reactor.dependents:
            if d not in __reactor__:
                errors.append(
                    "In Cell '{}': {}', dependent: {} cell doesn't exist."
                    .format(name, reactor, d))
    # log the errors somehow
    print("\n".join(errors))
    return errors == []


def run(detect_change_fn):
    # Run all the inputs cells for changes (need some kind of changed function
    # and for each one, run any of the dependents.  Note, that, the input cells
    # aren't changing; only detection of the change.  Thus, calculating the
    # dependency graph is a bit easier, as each time a cell is re-calculated,
    # we use the 'changed' function to see if it has, and then add it to a
    # queue until there are no more changes.
    global __reactor__
    # initialse the queue with changed inputs
    queue = collections.deque(
        (d for d in __reactor__.values()
         if d.type_ == Type.INPUT))
    processed = {}
    print("Before queue: ", queue)
    print("\n")
    # while we have a queue, call the function on the reactor cell, ask if it
    # has changed, and then if it has, add the dependents to the queue.
    while queue:
        cell = queue.popleft()
        print("queue: ", queue)
        print("cell: ", cell)
        print("processed: ", processed.keys())
        if cell.name in processed:
            print("already processed '{}', skipping".format(cell.name))
            continue
        print("\n")
        if cell.function:
            cell.function()
        processed[cell.name] = 1
        if detect_change_fn(cell.name):
            queue.extend((__reactor__[d] for d in cell.dependents
                          if d not in processed))
    # we ought to do some error handling, etc, so that we can recover from
    # issues, but that's basically it.


def f1():
    print("f() called")


def f2():
    print("f2() called")


def detect_change(*args):
    print("detect_change: ", args)
    return 'i' in args[0]


if __name__ == '__main__':
    # let's set up a test scenario
    add_input('i1')
    add_input('i2')
    add_compute('c1', f1, ('i1', 'i2'))
    add_compute('c2', f2, ('c1', ))
    print(__reactor__)
    _check_reactor()
    run(detect_change)

