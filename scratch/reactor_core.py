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
)

from exceptions import (
    KeyExists,
    AbortFunction,
    AbortExecution,
    ReactorError,
)


__reactor__ = collections.OrderedDict()


# ReactorItem is a tuple of representing an INPUT or COMPUTE item, each one can
# have multiple ReactorItemVariant items with different item, dependencies, and
# predicates to allow selecting a ReactorItem depending on some predicates
# (which may also involve looking at the context).
ReactorItem = collections.namedtuple(
    'ReactorItem', 'type_, key, name, variants, dependents')
ReactorItemVariant = collections.namedtuple(
    'ReactorItemVariant', 'item, dependencies, predicates, persistent')
ResolvedItem = collections.namedtuple(
    'ResolvedItem',
    'type_, key, name, item, dependents, dependencies, persistent')
Type = enum.Enum('Type', 'INPUT COMPUTE')


# TODO: turn this into a proper logging function
def log_exception(e):
    """Log the exception and traceback"""
    print(str(e))
    import traceback
    print(traceback.format_exc())


def key_exists(key):
    return maybe_format_key(key) in __reactor__


def _assert_valid_entry(reactor, name, new_is_default):
    """Check that name, along with the new_is_default flag, will only produce a
    single default or no defaults.  We can't have multiple defaults for a key
    name, and thus we trap it when it happens.

    :param reactor: the reactor to work on
    :param name: (String) key name
    :param new_is_default: the next entry will be a default.
    :raises AssertionError: if there is already a default
    """
    key = maybe_format_key(name)
    # if the new one isn't a default then it's going to be okay
    if not new_is_default or key not in reactor:
        return
    for item in reactor[key].variants:
        if not item.predicates:
            # a default already exists
            raise AssertionError("A default already exists for key '{}'"
                                 .format(name))


def add_input(*args, **kwargs):
    global __reactor__
    return _add_input(__reactor__, *args, **kwargs)


def _add_input(reactor, name, storable, predicates=None, persistent=True):
    """Add an input cell to the reactor, with the function 'function'.

    The `storable` is the item to put in the context.  If predicates is not
    None then multiple storables may be added (via multiple calls to add_input)
    and the FIRST to have all predicates as True will be used on a first added
    basis.  `storable` is either a callable (no parameters) or a value.

    If predicates is not None, then all but one calls to add_input() with the
    same `name` have to have predicates, except for one, which will be the
    default storable for that `name`.

    :param reactor: the reactor to work on
    :param name: the name of the input
    :param storable: the item to store in the cell/context
    :param predicates: an OPTIONAL list of predicates to decide which storable
        to store in the context.
    :param persistent: boolean, if True, it is persistent, if False ALWAYS
        changed.
    :raises AssertionError: if multiple defaults are provided.
    """
    global __reactor__
    _assert_valid_entry(reactor, name, (predicates is None))
    key = maybe_format_key(name)
    if key not in reactor:
        reactor[key] = ReactorItem(Type.INPUT, key, name, [], set())
    elif reactor[key].type_ != Type.INPUT:
        raise ReactorError(
            "Attempting to add an input to cell '{}' that is a '{}'"
            .format(key, reactor[key].type_))
    reactor[key].variants.append(
        ReactorItemVariant(storable, [], predicates or {}, persistent))


def add_compute(*args, **kwargs):
    global __reactor__
    _add_compute(__reactor__, *args, **kwargs)


def _add_compute(reactor, name, function, dependencies,
                 predicates=None, persistent=True):
    """Add a compute cell with dependencies.  Note that they don't actually
    have to exist; this will be checked when the 'run()' function is invoked
    which will do a consistency check on the reactor core before proceeding.

    The `function` is the item to put in the context.  If predicates is not
    None then multiple functions may be added (via multiple calls to add_input)
    and the FIRST to have all predicates as True will be used on a first added
    basis.  `function` is a callable.

    If predicates is not None, then all but one calls to add_compute() with the
    same `name` have to have predicates, except for one, which will be the
    default function for that `name`.

    :param reactor: the reactor to work with
    :param name: the cell's name
    :param function: what to call for the function
    :param dependencies: list of cell names as dependencies that trigger this
        function.
    :param predicates: an OPTIONAL list of predicates to decide which function
        to store in the context.
    :param persistent: boolean, default True, that if False, means that the
        cell is always 'changed' after computation.
    """
    _assert_valid_entry(reactor, name, (predicates is None))
    assert callable(function), ("Param function must be callable for key '{}'"
                                .format(name))
    key = maybe_format_key(name)
    dependencies_keys = [maybe_format_key(d) for d in dependencies]
    # look for a simple circular dependency
    if name in dependencies:
        raise KeyExists(
            "The dependency '{}' is the name of the compute.".format(name))
    if key not in reactor:
        reactor[key] = ReactorItem(Type.COMPUTE, key, name, [], set())
    elif reactor[key].type_ != Type.COMPUTE:
        raise ReactorError(
            "Attempting to add a compute to cell '{}' that is a '{}'"
            .format(key, reactor[key].type_))
    reactor[key].variants.append(
        ReactorItemVariant(function,
                           dependencies_keys,
                           predicates or {},
                           persistent))


def _calculate_dependents(reactor):
    """Calculate all of the forward dependents from the dependency lists in all
    the variants for all the items.  Note that dependents is a set() and so
    will only have unique items.

    :param reactor: the reactor to work on
    :raises ReactorError: if the dependencies don't exist as key names
    """
    errors = []
    for key, reactor_item in reactor.items():
        for variant in reactor_item.variants:
            for d in variant.dependencies:
                try:
                    reactor[d].dependents.add(key)
                except KeyError:
                    errors.append("formatted_key({}) not in reactor".format(d))
    if errors:
        raise ReactorError(
            "Formatted keys not found when checking dependencies: {}".
            format(", ".join(errors)))


def _check_reactor(reactor):
    """check the reactor for circular dependencies.
    NOTE: _calculate_dependents() must have been called as otherwise there
    will be nothing to check.

    :param reactor: the reactor to check.
    :raises ReactorError: if there is a problem
    """
    errors = []
    for key, reactor_item in reactor.items():
        try:
            _check_circular_dependencies(reactor,
                                         [key],
                                         reactor_item.dependents)
        except ReactorError as e:
            errors.append(str(e))
    if errors:
        raise ReactorError("Reactor has circular dependencies: '{}'"
                           .format(", ".join(errors)))


def _check_circular_dependencies(reactor, path, dependents):
    """Check for circular dependencies for any of the keys in path and
    descending into the remaining dependents.  A separate error string is
    generated and if there are any errors, ReactorError() is generated.

    :param reactor: the reactor to look at.
    :param path: the current path of keys to be examined.
    :param dependents: the set() of dependents to look at.
    :raises ReactorError: in the event of a circular dependency
    """
    errors = []
    for i, key in enumerate(path):
        if key in dependents:
            errors.append("{} has a cicular dependency with key: '{}'"
                          .format("->".join(path[i:]), key))
            if reactor[key].dependents:
                try:
                    _check_circular_dependencies(reactor,
                                                 path + key,
                                                 reactor[key].dependents)
                except ReactorError as e:
                    errors.append(str(e))
    if errors:
        raise ReactorError(", ".join(errors))

"""
Understanding how the reactor is run.

1. We want to run things that have changed inputs.
2. We have to ensure that anything that runs, also needs it's dependencies to
have already run.
3. We only want to run a function once.

This probably means building a tree structure, or something, to ensure that all
the functions which should be run, are run.

So an algorithm might look like this:

1. Queue all the inputs.
2. For an item in the queue, provided it is not already processed
  a) resolve the item to use (check the predicates, or if none, grab the
  default)
  b) Apply the item.  If no persistence or the item has changed, find the
  dependents.
  c) For each dependent, check the dependent's dependencies, and if they are
  not in the queue, or processed, add them to the queue too.  Then add the
  dependent item.  This is likely to be recursive, to ensure that the entire
  depenency chain is available for each of the dependents.


A reactor function or value can raise `AbortFunction` or `AbortExecution` to
stop either the current run of dependents, or abort the whole reactor (which
also avoids storing anything back to the kv store; i.e. the execution never
happened.  `AbortExecution` is essentially a charm in error state, and thus,
will probably be retried.  It's a fatal flaw.  `AbortFunction` is simply to
stop the current function and any dependents of that function.  The abort is
logged, but other functions carry on.

It would be even better if we could restrict the context values that a function
can access using the dependencies; i.e. they simply wouldn't be available to
the function to work with.  A function would declare what it needs that that
would be provided on the read-only context available to the function.
"""


def _resolve_item(reactor_item):
    """Resolve the reactor_item to run.  Do this by evaluating the predicates,
    for the first one that gets 'all true', return that one.  If a predicate
    raises an error, then it gets passed up the chain; e.g. if a predicate
    tries to access something it is not allowed, then it might throw an error,
    which causes the charm to bail.

    :param reactor_item: a ReactorItem namedtuple
    :returns: ResolvedItem() or None
    :raises: AbortExecution if the predicates raise an exception
    """
    default = None
    select = None
    for variant in reactor_item.variants:
        if not variant.predicates:
            default = variant
            continue
        # evalutate the predicates on this one
        try:
            if all((p() for p in variant.predicates)):
                select = variant
                break
        except Exception as e:
            log_exception(e)
            raise AbortExecution("a predicate on '{}' raised an exception: {}"
                                 .format(reactor_item, e))
    else:
        if default:
            select = default
        else:
            return None
    return ResolvedItem(reactor_item.type_,
                        reactor_item.key,
                        reactor_item.name,
                        select.item,
                        reactor_item.dependents,
                        select.dependencies,
                        select.persistent)


def _find_unprocessed_dependencies(processed, resolved_item):
    """Return a generator which outputs dependencies which haven't yet been
    processed.  This is so that they can be queued before this item, if this
    item has come to the beginning of the queue.

    :param processed: (set) formatted keys that have been processed.
    :param resolved_item: A ResolvedItem()
    :return: a generator which yields unprocessed keys.
    """
    for d in resolved_item.dependencies:
        if d not in processed:
            yield d


def _process_item(resolved_item, context_fn):
    """Process an item, assuming that the dependencies all exist.  If they
    don't then the access to the context the reactor provides will break.

    If the item is a Type.INPUT then, (check if it is callable) and if so,
    resolve it using a Callable.

    If the item is a Type.COMPUTE then assemble a context for it using the
    dependencies list, and call the function with that context.

    Returns the value either of the INPUT or the computed COMPUTE.

    May throw any error, depending on the function.  All errors are logged
    locally, and the error message is written to the charm log.  Any Exception
    other that AbortFunction is rethrown as an AbortExecution to terminate the
    charm, as other exceptions are considered 'program errors' rather than
    execution errors.

    :param resolved_item: a ResolvedItem()
    :param context_fn: context_fn(dependencies) -> context with just those
        dependencies.
    :returns: the value of the INPUT or result of the COMPUTE
    :raises AbortFunction: if the function raises that exception.
    :raises AbortExecution: if the function raises any other exception
    """
    try:
        if resolved_item.type_ == Type.INPUT:
            value = resolved_item.item
            while callable(value):
                value = value()
            return value
        elif resolved_item.type_ == Type.COMPUTE:
            # TODO: change context.context(...) to accept a limited return set.
            return resolved_item.item(context_fn(resolved_item.dependencies))
    except (AbortFunction, AbortExecution):
        raise
    except Exception as e:
        log_exception(e)
        raise AbortExecution("Aborted: Cell '{}' raise Exception: {}"
                             .format(resolved_item, e))
    # unexpected type
    raise AbortExecution("Got unexpected type: {} for item: {}"
                         .format(resolved_item.type_, resolved_item))


def _initialise_queue_with_inputs(reactor):
    """Initialise the queue (a list) with just the inputs, resolve those
    inputs to ResolveItem() elements, and return that list.  This means that
    the predicates for those input elements, if they exist, will be run to
    choose the correct variant for the input.

    :param reactor: the reactor to work on
    :returns: a generator of ResolvedItem() of type Type.INPUT
    :raises AbortException: if one of the predicates raises an exception
    """
    for item in reactor.values():
        if item.type_ == Type.INPUT:
            yield _resolve_item(item)


def run(*args, **kwargs):
    global __reactor__
    return _run(__reactor__)


def _run(reactor, detect_change_fn, get_context_fn, set_context_fn):
    """Run the reactor, starting with the inputs.

    This preloads all of the inputs, picks the right one, according to the
    predicates, and then uses the detect_change_fn to determine whether to run
    the dependent functions.  This continues until there is nothing left to
    run.  The run then exits.

    The function can raise AbortExecution, which means that the processing came
    to an end.  The caller should assume that the charm has failed and NOT
    store any results from the context, and assume that the hook has failed
    (and log that this is the case).

    :param reactor: the reactor to work on.
    :param detect_change_fn: detect_change_fn(key) -> boolean
    :param get_context_fn: get_context_fn(list) -> context
    :param set_context_fn: set_context_fn(key, value) -> None
    :raises: AbortExecution() if a dependent functions fails or raises this
        explicitly to exit the hook.
    """
    # function may raise AbortExecution
    queue = collections.deque(_initialise_queue_with_inputs(reactor))
    processed = set()
    while queue:
        peek_cell = queue[0]
        if peek_cell.key in processed:
            queue.popleft()
            continue
        for d in _find_unprocessed_dependencies(processed, peek_cell):
            queue.appendleft(_resolve_item(reactor[d]))
        queue.extendleft(
            (_resolve_item(reactor[d])
             for d in _find_unprocessed_dependencies(processed, peek_cell)))
        if peek_cell != queue[0]:
            # retry the next item if we've found unprocessed items
            continue
        cell = queue.popleft()
        try:
            value = _process_item(cell, get_context_fn)
        except AbortFunction:
            # we add this as processed, because even though it aborted, it
            # still has to show as done.
            processed.add(cell.key)
            set_context_fn(cell.name, None)
            continue
        except AbortExecution:
            raise
        except Exception as e:
            # somethignvery odd happened
            raise AbortExecution("Weirdness: '{}' occured with '{}'"
                                 .format(e, cell))
        # store the value in the context, and add it to processed.
        processed.add(cell.key)
        set_context_fn(cell.name, value)
        if not cell.persistent or detect_change_fn(cell.name):
            queue.extend((_resolve_item(reactor[d]) for d in cell.dependents
                          if d not in processed))


def f1(ctxt):
    print("f1() called with {}".format(ctxt))
    return ctxt['i1'] + ctxt['i2']


def f2(ctxt):
    print("f2() called with {}".format(ctxt))
    return ctxt['c1'] * 2


def detect_change(*args):
    print("detect_change: ", args)
    return 'i' in args[0] or args[0] == 'c1'


if __name__ == '__main__':
    # let's set up a test scenario
    add_input('i1', 1)
    add_input('i2', 2)
    add_compute('c1', f1, ('i1', 'i2'))
    add_compute('c2', f2, ('c1', ))
    _calculate_dependents(__reactor__)
    _check_reactor(__reactor__)
    print("Calculated  dependents, and checked reactor")
    import pprint
    pprint.pprint(__reactor__)
    ctxt = {}

    def get_item(l):
        return {k: v for k, v in ctxt.items() if k in l}

    def set_item(k, v):
        ctxt[k] = v

    _run(__reactor__, detect_change, get_item, set_item)
    print("ctxt afterwards is:", ctxt)
