import collections
import mock
import unittest

import charms.declarative.core.ro_types as ro_types


class TestResolveValue(unittest.TestCase):

    def test_resolve_value(self):
        self.assertEqual(ro_types.resolve_value(5), 5)
        self.assertTrue(isinstance(ro_types.resolve_value(lambda: 5),
                                   ro_types.Callable))
        self.assertTrue(isinstance(ro_types.resolve_value({}),
                                   ro_types.ReadOnlyDict))
        self.assertEqual(ro_types.resolve_value("hello"), "hello")
        self.assertTrue(isinstance(ro_types.resolve_value([]),
                                   ro_types.ReadOnlyList))
        self.assertTrue(isinstance(ro_types.resolve_value(tuple()),
                                   ro_types.ReadOnlyList))


class TestCallable(unittest.TestCase):

    def test_only_accepts_callables(self):

        class Tester():
            pass

        with self.assertRaises(AssertionError):
            ro_types.Callable(5)
        with self.assertRaises(AssertionError):
            ro_types.Callable("hello")
        with self.assertRaises(AssertionError):
            ro_types.Callable(Tester())

    def test_accepts_callable(self):
        ro_types.Callable(lambda: 5)

    def test_resolves_multiple_levels_of_callable(self):
        f = lambda: 5
        ff = lambda: f
        fff = lambda: ff
        x = ro_types.Callable(fff)
        self.assertEqual(x(), 5)

    def test_verify_that_it_caches(self):
        m = mock.Mock()
        m.return_value = 1
        f = lambda: m()
        x = ro_types.Callable(f)
        self.assertEqual(x(), 1)
        self.assertEqual(x(), 1)
        m.assert_called_once_with()

    def test_is_read_only(self):
        c = ro_types.Callable(lambda: 5)
        with self.assertRaises(TypeError):
            c.three = 3

    def test_has_repr_and_doesnt_resolve_callable(self):
        m = mock.Mock()
        m.return_value = 1
        c = ro_types.Callable(m)
        self.assertTrue(c.__repr__().startswith("Callable("))
        self.assertTrue(c.__repr__().endswith(")"))
        m.assert_not_called()
        c()
        self.assertEqual(c.__repr__(), "Callable(lambda: 1)")

    def test_has_str_and_doesnt_resolve_callable(self):
        m = mock.Mock()
        m.return_value = 1
        c = ro_types.Callable(m)
        self.assertTrue(str(c).startswith("<Callable("))
        self.assertTrue(str(c).endswith(")>"))
        m.assert_not_called()
        c()
        self.assertEqual(str(c), "1")

    def test_has_serialize_method(self):
        m = mock.Mock()
        m.return_value = {"a": {"b": 3}}
        c = ro_types.Callable(m)
        # verify that it does resolve the callable
        s = c.__serialize__()
        m.assert_called_once_with()
        self.assertEqual(s, '{"a":{"b":3}}')


class TestReadOnlyWrapperDict(unittest.TestCase):

    def test_init_only_allows_mapping_items(self):
        with self.assertRaises(AssertionError):
            ro_types.ReadOnlyWrapperDict([])
        with self.assertRaises(AssertionError):
            ro_types.ReadOnlyWrapperDict(1)
        with self.assertRaises(AssertionError):
            ro_types.ReadOnlyWrapperDict("Hello")
        ro_types.ReadOnlyWrapperDict({})
        ro_types.ReadOnlyWrapperDict(collections.OrderedDict())

    def test_init_copies_items(self):
        d = {'a': 1, 'b': 2}
        x = ro_types.ReadOnlyWrapperDict(d)
        d['a'] = 3
        self.assertEqual(x['a'], 1)

    def test_getitem(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1, 'b': 2})
        self.assertEqual(x['a'], 1)
        self.assertEqual(x['b'], 2)

    def test_getattr(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1, 'b': 2})
        self.assertEqual(x.a, 1)
        self.assertEqual(x.b, 2)

    def test_getattr_not_an_item(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1})
        with self.assertRaises(AttributeError):
            x.b

    def test_setattr(self):
        with self.assertRaises(TypeError):
            x = ro_types.ReadOnlyWrapperDict({'a': 1, 'b': 2})
            x.hello = 1

    def test_setitem(self):
        with self.assertRaises(TypeError):
            x = ro_types.ReadOnlyWrapperDict({'a': 1, 'b': 2})
            x['hello'] = 1

    def test_len(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1, 'b': 2})
        self.assertEqual(len(x), 2)

    def test_iter(self):
        x = ro_types.ReadOnlyWrapperDict(
            collections.OrderedDict([('a', 1), ('b', 2)]))
        self.assertEqual(list(x.items()), [('a', 1), ('b', 2)])

    def test_repr(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1})
        self.assertEqual(repr(x), "ReadOnlyWrapperDict({'a': 1})")

    def test_str(self):
        x = ro_types.ReadOnlyWrapperDict({'a': 1})
        self.assertEqual(str(x), "{'a': 1}")

    def test_serialize(self):
        x = ro_types.ReadOnlyWrapperDict(
            collections.OrderedDict([('a', 1), ('b', 2)]))
        # self.assertEqual(x.__serialize__(), '{"a":1,"b":2}')
        self.assertEqual(x.__serialize__(), {"a": 1, "b": 2})


class TestReadOnlyDict(unittest.TestCase):

    def test_init(self):
        # should only allow things that can be mapped (e.g. dictionary)
        # and that have a copy() function
        with self.assertRaises(AssertionError):
            x = ro_types.ReadOnlyDict([])
        # should work with a dictionary
        x = ro_types.ReadOnlyDict({'a': 1, 'b': 2})
        # should work with an OrderedDict
        x = ro_types.ReadOnlyDict(collections
                                  .OrderedDict([('a', 1), ('b', 2)]))
        # check that the data is copied
        b = {'a': 1}
        x = ro_types.ReadOnlyDict(b)
        b['a'] = 2
        self.assertEqual(x['a'], 1)

    def test_getitem(self):
        x = ro_types.ReadOnlyDict({'a': 1, 'b': lambda: 5})
        self.assertEqual(x['a'], 1)
        self.assertEqual(x['b'], 5)
        with self.assertRaises(KeyError):
            x['c']

    def test_getattr(self):
        x = ro_types.ReadOnlyDict({'a': 1, 'b': lambda: 5})
        self.assertEqual(x.a, 1)
        self.assertEqual(x.b, 5)
        with self.assertRaises(KeyError):
            x.c

    def test_setattr(self):
        x = ro_types.ReadOnlyDict({'a': 1, 'b': lambda: 5})
        with self.assertRaises(TypeError):
            x.c = 1

    def test_setitem(self):
        x = ro_types.ReadOnlyDict({'a': 1, 'b': lambda: 5})
        with self.assertRaises(TypeError):
            x['c'] = 1

    def test_iter(self):
        x = ro_types.ReadOnlyDict(collections
                                  .OrderedDict([('a', 1),
                                                ('b', lambda: 5)]))
        self.assertEqual(list(iter(x)), [('a', 1), ('b', 5)])

    def test_serialize(self):
        x = ro_types.ReadOnlyDict({'a': 1})
        self.assertEqual(x.__serialize__(), {'a': 1})


class TestReadOnlyList(unittest.TestCase):

    def test_create_new_tuple(self):
        x = ro_types.ReadOnlyList([1, 2, lambda: 3])
        self.assertEqual(x[0], 1)
        self.assertEqual(x[1], 2)
        self.assertEqual(x[2], 3)
        self.assertEqual(len(x), 3)
        # also check that the dicts and lists become readonly
        x = ro_types.ReadOnlyList([[], {}, lambda: 1])
        self.assertTrue(isinstance(x[0], ro_types.ReadOnlyList))
        self.assertTrue(isinstance(x[1], ro_types.ReadOnlyDict))
        # note that it becomes 1, because it was a lambda
        self.assertEqual(x[2], 1)

    def test_iter(self):
        x = ro_types.ReadOnlyList([1, 2, lambda: 3])
        self.assertEqual(list(iter(x)), [1, 2, 3])

    def test_repr(self):
        x = ro_types.ReadOnlyList([1, 2, 3])
        self.assertEqual(repr(x), "ReadOnlyList((1, 2, 3))")

    def test_str(self):
        x = ro_types.ReadOnlyList([1, 2, 3])
        self.assertEqual(str(x), "(1, 2, 3)")

    def test_serialize(self):
        x = ro_types.ReadOnlyList([1, 2, lambda: 3])
        self.assertEqual(x.__serialize__(), [1, 2, 3])

    def test_is_readonly(self):
        x = ro_types.ReadOnlyList([1, 2, lambda: 3])
        with self.assertRaises(TypeError):
            x[0] = 2
        with self.assertRaises(TypeError):
            x.hello = 4


class TestContextJSONEncoder(unittest.TestCase):

    def test_encode_structure(self):
        a = collections.OrderedDict([('a', 1), ('b', 2), ('c', lambda: 3)])
        b = [1, 2, 3]
        c = lambda: 4
        aa = ro_types.ReadOnlyDict(a)
        bb = ro_types.ReadOnlyList(b)
        cc = ro_types.Callable(c)
        x = collections.OrderedDict([('x', aa), ('y', bb), ('z', cc)])
        xx = ro_types.ReadOnlyWrapperDict(x)
        self.assertEqual(
            ro_types
            .ContextJSONEncoder(**ro_types.JSON_ENCODE_OPTIONS)
            .encode(xx),
            '{"x":{"a":1,"b":2,"c":"3"},"y":[1,2,3],"z":4}')
