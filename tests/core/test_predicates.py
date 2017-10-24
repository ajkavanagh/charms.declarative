import unittest

import charms.declarative.core.predicates as pred


class TestDeferredBasicStringComparitor(unittest.TestCase):

    class Comparitor(pred.DeferredBasicStringComparitor):

        _list = ('apple', 'cherry', 'banana', 'kiwi', 'damson')

    def test_string_comparitor_returns_callable(self):
        p = self.Comparitor('cherry')
        x = p > 'apple'
        self.assertTrue(isinstance(x, pred.Callable))

    def test_string_comparitor(self):
        p = self.Comparitor('cherry')
        f = lambda x: x()
        self.assertTrue(f(p > 'apple'))
        self.assertTrue(f(p < 'banana'))
        self.assertTrue(f(p == 'cherry'))
        self.assertTrue(f(p != 'kiwi'))
        self.assertTrue(f(p >= 'cherry'))
        self.assertTrue(f(p <= 'banana'))
        # and reversed??
        self.assertTrue(f('apple' < p))
        self.assertTrue(f('banana' >= p))

    def test_string_comparitor_not_in_list(self):
        with self.assertRaises(KeyError):
            self.Comparitor('pineapple')

    def test_string_comparitor_compare_not_in_list(self):
        p = self.Comparitor('cherry')
        with self.assertRaises(KeyError):
            self.assertTrue(p > 'pineapple')

    def test_str(self):
        self.assertEqual(str(self.Comparitor('cherry')), 'cherry')

    def test_repr(self):
        self.assertEqual(repr(self.Comparitor('cherry')),
                         "Comparitor(index=1, _list=('apple', 'cherry',"
                         " 'banana', 'kiwi', 'damson'))")

    def test_base_class_checks_for_list(self):
        with self.assertRaises(RuntimeError):
            p = pred.DeferredBasicStringComparitor('helo')


class TestPredicates(unittest.TestCase):

    def test_p_any(self):
        self.assertIsInstance(pred.p_any(), pred.Callable)
        self.assertTrue(pred.p_any(True, False)())
        self.assertTrue(pred.p_any(lambda: True, lambda: False)())
        self.assertFalse(pred.p_any(False, False)())

    def test_p_all(self):
        self.assertIsInstance(pred.p_all(), pred.Callable)
        self.assertFalse(pred.p_all(True, False)())
        self.assertFalse(pred.p_all(lambda: True, lambda: False)())
        self.assertTrue(pred.p_all(True, True)())

    def test_p_none(self):
        self.assertIsInstance(pred.p_none(), pred.Callable)
        self.assertTrue(pred.p_none(True, False)())
        self.assertTrue(pred.p_none(lambda: True, lambda: False)())
        self.assertFalse(pred.p_none(True, True)())

    def test_p_not(self):
        self.assertIsInstance(pred.p_not(True), pred.Callable)
        self.assertTrue(pred.p_not(False)())
        self.assertFalse(pred.p_not(True)())
        self.assertTrue(pred.p_not(lambda: False)())
        self.assertFalse(pred.p_not(lambda: True)())

    def test_make_an_xor(self):
        # (not(a) and b) or (a and not(b))
        # 0 xor 0 = 0
        # 1 xor 0 = 1
        # 0 xor 1 = 1
        # 1 xor 1 = 0
        def f(a, b):
            return pred.p_or(pred.p_and(pred.p_not(lambda: a), lambda: b),
                             pred.p_and(lambda: a, pred.p_not(lambda: b)))

        self.assertFalse(f(False, False)())
        self.assertTrue(f(True, False)())
        self.assertTrue(f(False, True)())
        self.assertFalse(f(True, True)())


class TestP(unittest.TestCase):

    def test_returns_callable(self):
        x = pred.P(4) > 2
        self.assertIsInstance(x, pred.Callable)

    def test_lhs(self):
        p = pred.P(4)
        f = lambda x: x()
        self.assertTrue(f(p > 2))
        self.assertFalse(f(p < 2))
        self.assertTrue(f(p >= 4))
        self.assertTrue(f(p <= 4))
        self.assertFalse(f(p != 4))
        self.assertTrue(f(p != 3))
        # verify for a string too
        p = pred.P('hello')
        self.assertTrue(f(p == 'hello'))
        self.assertFalse(f(p == 'goodbye'))
        self.assertTrue(f(p != 'goodbye'))

    def test_rhs(self):
        p = pred.P(4)
        f = lambda x: x()
        self.assertTrue(f(2 < p))
        self.assertFalse(f(2 > p))
        self.assertTrue(f(4 <= p))
        self.assertTrue(f(4 >= p))
        self.assertFalse(f(4 != p))
        self.assertTrue(f(3 != p))
        # verify for a string too
        p = pred.P('hello')
        self.assertTrue(f('hello' == p))
        self.assertFalse(f('goodbye' == p))
        self.assertTrue(f('goodbye' != p))

    def test_str(self):
        self.assertEqual(str(pred.P(4)), '4')
        self.assertEqual(str(pred.P('hello')), 'hello')

    def test_repr(self):
        self.assertEqual(repr(pred.P(4)), 'P(item=4)')
        self.assertEqual(repr(pred.P('hello')), "P(item='hello')")
