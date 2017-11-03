import collections
import mock
import unittest

import charms.declarative.core.context as context
import charms.declarative.core.ro_types as ro_types
import charms.declarative.core.utils as utils


class TestContext(unittest.TestCase):

    def test_set_context(self):
        ctxt = {}
        context.set_context('hello', 1, _context=ctxt)
        self.assertEqual(ctxt['hello'], 1)
        context.set_context('goodbye', lambda: 5, _context=ctxt)
        self.assertTrue(isinstance(ctxt['goodbye'], ro_types.Callable))
        context.set_context('a', [], _context=ctxt)
        context.set_context('b', {}, _context=ctxt)
        self.assertTrue(isinstance(ctxt['a'], ro_types.ReadOnlyList))
        self.assertTrue(isinstance(ctxt['b'], ro_types.ReadOnlyDict))
        # check key formatting is working
        context.set_context('a-b', 1, _context=ctxt)
        self.assertEqual(ctxt[utils.maybe_format_key('a-b')], 1)

        # test the global works too.
        with mock.patch.object(context, '__context__', new={}):
            context.set_context('a', 5)
            self.assertEqual(context.__context__['a'], 5)

    def test_set_context_duplicate_key(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        with self.assertRaises(context.KeyExists):
            context.set_context('a', 10, _context=ctxt)

    def test_get_context(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        x = context.context('a', _context=ctxt)
        self.assertEqual(x.a, 10)
        context.set_context('b', lambda: 5, _context=ctxt)
        x = context.context('a', _context=ctxt)
        self.assertEqual(x.a, 10)
        self.assertEqual(len(x), 1)
        # now get both of them
        x = context.context(_context=ctxt)
        self.assertEqual(x.b, 5)
        self.assertEqual(x['b'], 5)
        self.assertEqual(x['a'], 10)
        self.assertEqual(len(x), 2)
        # get just b
        x = context.context(['b'], _context=ctxt)
        self.assertEqual(len(x), 1)
        self.assertEqual(x.b, 5)

    def test_get_context_pass_neither_string_not_iterable(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        with self.assertRaises(RuntimeError):
            context.context(object, _context=ctxt)

    def test_get_context_pass_missing_key(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        with self.assertRaises(KeyError):
            context.context('b', _context=ctxt)

    def test_get_context_using_global(self):
        with mock.patch.object(context, '__context__', new={}):
            context.set_context('a', 10)
            x = context.context('a')
            self.assertTrue(x.a, 10)

    def test_key_exists(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        self.assertTrue(context.key_exists('a', _context=ctxt))

    def test_key_exists_using_global(self):
        with mock.patch.object(context, '__context__', new={}):
            context.set_context('a', 10)
            self.assertTrue(context.key_exists('a'))

    def test_serialize_key(self):
        ctxt = collections.OrderedDict()
        context.set_context('a', 10, _context=ctxt)
        context.set_context('b', lambda: 5, _context=ctxt)
        # serialise just a and then b
        self.assertEqual(context.serialize_key('a', _context=ctxt), '10')
        self.assertEqual(context.serialize_key('b', _context=ctxt), '5')
        # serialize both of them
        self.assertEqual(context.serialize_key(_context=ctxt),
                         '{"a":10,"b":5}')
        # and serialize neither of them
        self.assertEqual(context.serialize_key('c', _context=ctxt), None)

    def test_serialize_key_using_global(self):
        with mock.patch.object(context, '__context__',
                               new=collections.OrderedDict()):
            context.set_context('a', 10)
            context.set_context('b', lambda: 5)
            self.assertEqual(context.serialize_key(),
                             '{"a":10,"b":5}')

    def test_copy(self):
        ctxt = collections.OrderedDict()
        # set the copy BEFORE the 'a' has been set (prove it's late)
        context.set_context('b',
                            context.copy('a', _context=ctxt),
                            _context=ctxt)
        context.set_context('a', 10, _context=ctxt)
        x = context.context(_context=ctxt)
        self.assertEqual(x.a, x.b)

    def test_copy_using_global(self):
        with mock.patch.object(context, '__context__',
                               new=collections.OrderedDict()):
            # set the copy BEFORE the 'a' has been set (prove it's late)
            context.set_context('b', context.copy('a'))
            context.set_context('a', lambda: 10)
            x = context.context()
            self.assertEqual(x.b, x.a)
