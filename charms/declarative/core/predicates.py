from charms.declarative.core.ro_types import (
    Callable,
)


class DeferredBasicStringComparitor(object):
    """Provides a class that will compare strings from an iterator type object.
    (very similar to the BasicStringComparitor() in charm-helpers)

    However, this version provides a deferred version, which returns functions
    that can be evaluated to produce the result.

    Used to provide > and < comparisons on strings that may not necessarily be
    alphanumerically ordered.  e.g. OpenStack or Ubuntu releases AFTER the
    z-wrap.

    Note that the deferrable is a Callable() which means that it caches on
    first call.
    """

    _list = None

    def __init__(self, item):
        if self._list is None:
            raise Exception("Must define the _list in the class definition!")
        try:
            self.index = self._list.index(item)
        except Exception:
            raise KeyError("Item '{}' is not in list '{}'"
                           .format(item, self._list))

    def __eq__(self, other):
        assert isinstance(other, str) or isinstance(other, self.__class__)
        if other not in self._list:
            raise KeyError("Item '{}' is not in list '{}'"
                           .format(other, self._list))
        return Callable(lambda: self.index == self._list.index(other))

    def __ne__(self, other):
        return Callable(lambda: not self.__eq__(other)())

    def __lt__(self, other):
        if other not in self._list:
            raise KeyError("Item '{}' is not in list '{}'"
                           .format(other, self._list))
        assert isinstance(other, str) or isinstance(other, self.__class__)
        return Callable(lambda: self.index < self._list.index(other))

    def __ge__(self, other):
        return Callable(lambda: not self.__lt__(other)())

    def __gt__(self, other):
        assert isinstance(other, str) or isinstance(other, self.__class__)
        if other not in self._list:
            raise KeyError("Item '{}' is not in list '{}'"
                           .format(other, self._list))
        return Callable(lambda: self.index > self._list.index(other))

    def __le__(self, other):
        return Callable(lambda: not self.__gt__(other)())

    def __str__(self):
        """Always give back the item at the index so it can be used in
        comparisons like:

        s_mitaka = CompareOpenStack('mitaka')
        s_newton = CompareOpenstack('newton')

        assert s_newton > s_mitaka

        @returns: <string>
        """
        return self._list[self.index]

    def __repr__(self):
        return "{}(index={}, _list={})".format(self.__class__.__name__,
                                               repr(self.index),
                                               repr(self._list))


def _resolve_callable(c):
    """Helper to resolve a callable to its value, even if they are embedded.

    :param c: FN() -> value-or-callable
    :returns: fn(fn(fn....))
    :raises: possibly anything, depending on the callable
    """
    while callable(c):
        c = c()
    return c


def p_any(*predicates):
    """Return a lambda that evaluates to True if ANY the predicates passed are
    truthy.  The predicates can be functions or values.

    :param predicates: a list of callables or values
    :returns: Callable(fn: -> boolean)
    :raises: may raise anything, depending on the callables
    """
    return Callable(lambda: any((_resolve_callable(p) for p in predicates)))


p_or = p_any


def p_all(*predicates):
    """Return a lambda that evaluates to True if ALL the predicates passed are
    Truely.  The predicates can be functions or values.

    :param predicates: a list of callables or values
    :returns: Callable(fn: -> boolean)
    :raises: may raise anything, depending on the callables
    """
    return Callable(lambda: all((_resolve_callable(p) for p in predicates)))


p_and = p_all


def p_none(*predicates):
    """Return a lambda that evaluates to True if NONE the predicates passed are
    Truely.  The predicates can be functions or values.

    :param predicates: a list of callables or values
    :returns: Callable(fn: -> boolean)
    :raises: may raise anything, depending on the callables
    """
    return Callable(lambda: not all((_resolve_callable(p)
                                     for p in predicates)))


def p_not(predicate):
    """Return a lambda that does the NOT of the predicate passed
    The predicate can be a value or a function

    :param predicate: a value or function (FN() -> ?)
    :returns: Callable(fn: -> boolean)
    :raises: may raise anything, depending on the callables
    """
    return Callable(lambda: not _resolve_callable(predicate))


class P(object):
    """Provides a class that will accept a single value on the init, and then
    provide a deferred comparison of that object with another as a lambda
    function that takes no values.  The intent is to be able to do:

    >>> P(something) > something else.

    This would return a callable that resolves the '>'.  However, not that the
    something and something-else would be called at the definition time.

    The something and something-else can both be callables, and if so are
    resolved to values before the comparison is performed.

    Note it actually returns a Callable(FN() -> something) rather than a
    straight lambda, as Callable caches the called value after it has been
    called for performance reasons.
    """

    def __init__(self, item):
        self.item = item

    def __eq__(self, other):
        return Callable(lambda: _resolve_callable(self.item) ==
                        _resolve_callable(other))

    def __ne__(self, other):
        return Callable(lambda: not self.__eq__(other)())

    def __lt__(self, other):
        return Callable(lambda: _resolve_callable(self.item) <
                        _resolve_callable(other))

    def __ge__(self, other):
        return Callable(lambda: not self.__lt__(other)())

    def __gt__(self, other):
        return Callable(lambda: _resolve_callable(self.item) >
                        _resolve_callable(other))

    def __le__(self, other):
        return Callable(lambda: not self.__gt__(other)())

    def __str__(self):
        return str(self.item)

    def __repr__(self):
        return "{}(item={})".format(self.__class__.__name__, repr(self.item))
