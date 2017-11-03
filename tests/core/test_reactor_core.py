import collections
import functools
import mock
import unittest

import charms.declarative.core.reactor_core as core


class TestUtilFunctions(unittest.TestCase):

    def test_log_exception(self):
        # this is just to get the coverage up
        try:
            raise Exception('hello')
        except Exception as e:
            core.log_exception(e)

    def test_key_exists(self):
        with mock.patch.object(core, '__reactor__', new={}) as r:
            r['a'] = 1
            self.assertTrue(core.key_exists('a'))


class TestReactorCoreValidEntry(unittest.TestCase):

    def test__assert_valid_entry_empty(self):
        core._assert_valid_entry({}, 'a', True)
        core._assert_valid_entry({}, 'a', False)

    def test__assert_valid_entry_not_empty(self):
        r = {}
        core._add_input(r, 'a', 1)
        # add a non_default -- should work
        core._assert_valid_entry(r, 'a', False)
        # default should fail
        with self.assertRaises(AssertionError):
            core._assert_valid_entry(r, 'a', True)
        # now the other way around (first has a predicate)
        r = {}
        core._add_input(r, 'a', 1, predicates=[True])
        # add a non_default -- should work
        core._assert_valid_entry(r, 'a', False)
        # a default should work
        core._assert_valid_entry(r, 'a', True)


class TestReactorCoreAddInput(unittest.TestCase):

    def test_add_input_using_global(self):
        with mock.patch.object(core, '__reactor__', new={}) as r, \
                mock.patch.object(core, '_add_input') as ai:
            core.add_input('a', 1, predicates=[True], persistent=False)
            ai.assert_called_once_with(r, 'a', 1, predicates=[True],
                                       persistent=False)

    def test_add_input_multiple(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        core._add_input(r, 'a_a', 2, [True])  # deliberately 'a_a'!
        core._add_input(r, 'a-a', 3, [False], persistent=False)
        # validate that they got there.
        self.assertEqual(len(r), 1)
        i = r['a_a']
        self.assertIsInstance(i, core.ReactorItem)
        self.assertEqual(i.type_, core.Type.INPUT)
        self.assertEqual(i.name, 'a-a')
        self.assertEqual(i.key, 'a_a')
        self.assertEqual(len(i.variants), 3)
        self.assertEqual(len(i.dependents), 0)
        # check each of the variants
        i0 = i.variants[0]
        i1 = i.variants[1]
        i2 = i.variants[2]
        self.assertEqual(i0.item, 1)
        self.assertEqual(i1.item, 2)
        self.assertEqual(i2.item, 3)
        self.assertEqual(len(i0.dependencies), 0)
        self.assertEqual(len(i1.dependencies), 0)
        self.assertEqual(len(i2.dependencies), 0)
        self.assertEqual(i0.predicates, [])
        self.assertEqual(i1.predicates, [True])
        self.assertEqual(i2.predicates, [False])
        self.assertEqual(i0.persistent, True)
        self.assertEqual(i1.persistent, True)
        self.assertEqual(i2.persistent, False)

    def test_add_input_multiple_defaults_should_fail(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        with self.assertRaises(AssertionError):
            core._add_input(r, 'a-a', 1)

    def test_add_input_onto_compute_fails(self):
        r = collections.OrderedDict()
        r['a'] = core.ReactorItem(core.Type.COMPUTE, 'a', 'a', [], set())
        with self.assertRaises(core.ReactorError):
            core._add_input(r, 'a', 1)


def add_compute_helper(r, *args, **kwargs):
    core._add_compute_or_output(r, core.Type.COMPUTE, *args, **kwargs)

def add_output_helper(r, *args, **kwargs):
    core._add_compute_or_output(r, core.Type.OUTPUT, *args, **kwargs)


class TestReactorCoreAddComputeOrOutput(unittest.TestCase):

    def test_add_compute_using_global(self):
        f = lambda: True
        with mock.patch.object(core, '__reactor__', new={}) as r, \
                mock.patch.object(core, '_add_compute_or_output') as ac:
            core.add_compute('a', f,
                             ['b'],
                             predicates=[True],
                             persistent=False)
            ac.assert_called_once_with(r, core.Type.COMPUTE, 'a', f, ['b'],
                                       predicates=[True],
                                       persistent=False)
            ac.reset_mock()
            core.add_output('a', f,
                            ['b'],
                            predicates=[True],
                            persistent=False)
            ac.assert_called_once_with(r, core.Type.OUTPUT, 'a', f, ['b'],
                                       predicates=[True],
                                       persistent=False)

    def test_add_compute_checks_for_callable(self):
        r = collections.OrderedDict()
        with self.assertRaises(AssertionError):
            add_compute_helper(r, 'a', None, [])
        # should just work
        add_compute_helper(r, 'a', lambda: True, [])

    def test_add_compute_multiple(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        core._add_input(r, 'a-b', 2)
        f1 = lambda c: c.a_a + 1
        f2 = lambda c: c.a_a + 2
        f3 = lambda c: c.a_a + 3
        # note keys are deliberately - and _ to check format key
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        add_compute_helper(r, 'b_b', f2, ['a-a'], predicates=[True])
        add_compute_helper(r, 'b-b', f3, ['a_b'], predicates=[False],
                           persistent=False)
        # check that the computes all got added okay
        self.assertEqual(len(r), 3)
        c = r['b_b']
        self.assertIsInstance(c, core.ReactorItem)
        self.assertEqual(c.type_, core.Type.COMPUTE)
        self.assertEqual(c.name, 'b-b')
        self.assertEqual(c.key, 'b_b')
        self.assertEqual(len(c.variants), 3)
        self.assertEqual(len(c.dependents), 0)
        # check each of the variants
        c0 = c.variants[0]
        c1 = c.variants[1]
        c2 = c.variants[2]
        self.assertIsInstance(c0, core.ReactorItemVariant)
        self.assertIsInstance(c1, core.ReactorItemVariant)
        self.assertIsInstance(c2, core.ReactorItemVariant)
        self.assertEqual(c0.item, f1)
        self.assertEqual(c1.item, f2)
        self.assertEqual(c2.item, f3)
        self.assertEqual(c0.dependencies, ['a_a'])
        self.assertEqual(c1.dependencies, ['a_a'])
        self.assertEqual(c2.dependencies, ['a_b'])
        self.assertEqual(c0.predicates, [])
        self.assertEqual(c1.predicates, [True])
        self.assertEqual(c2.predicates, [False])
        self.assertEqual(c0.persistent, True)
        self.assertEqual(c1.persistent, True)
        self.assertEqual(c2.persistent, False)

    def test_add_compute_multiple_defaults_should_fail(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        with self.assertRaises(AssertionError):
            add_compute_helper(r, 'b-b', f1, ['a-a'])

    def test_add_compute_dependency_is_name_of_compute(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        with self.assertRaises(core.KeyExists):
            add_compute_helper(r, 'b-b', f1, ['a-a', 'b_b'])

    def test_add_compute_variant_to_input_should_fail(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        core._add_input(r, 'b-b', 2, predicates=[True])
        f1 = lambda c: c.a_a + 1
        with self.assertRaises(core.ReactorError):
            add_compute_helper(r, 'b-b', f1, ['a-a'])


class TestCalculateDependents(unittest.TestCase):

    def test_empty_reactor_ok(self):
        r = collections.OrderedDict()
        core._calculate_dependents(r)

    def test_simple_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        core._calculate_dependents(r)
        # verify that the 'a-a' has the 'b-b' dependent
        i = r['a_a']
        self.assertEqual(len(i.dependents), 1)
        self.assertIn('b_b', i.dependents)

    def test_chain_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        f2 = lambda c: c.b_b + 2
        add_compute_helper(r, 'c-c', f2, ['b-b'])
        core._calculate_dependents(r)
        # verify that the 'a-a' has the 'b-b' dependent
        i = r['a_a']
        self.assertEqual(len(i.dependents), 1)
        self.assertIn('b_b', i.dependents)
        # verify that the 'b-b' has the 'c-c' dependent
        i = r['b_b']
        self.assertEqual(len(i.dependents), 1)
        self.assertIn('c_c', i.dependents)

    def test_pyramid_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        f2 = lambda c: c.a_a + 2
        add_compute_helper(r, 'c-c', f2, ['a-a'])
        core._calculate_dependents(r)
        # verify that the 'a-a' has the 'b-b' and 'c-c' dependents
        i = r['a_a']
        self.assertEqual(len(i.dependents), 2)
        self.assertIn('b_b', i.dependents)
        self.assertIn('c_c', i.dependents)

    def test_diamond_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        f2 = lambda c: c.a_a + 2
        add_compute_helper(r, 'c-c', f2, ['a-a'])
        f3 = lambda c: c.b_b + c.c_c
        add_compute_helper(r, 'd-d', f3, ['b-b', 'c-c'])
        core._calculate_dependents(r)
        # verify that the 'a-a' has the 'b-b' and 'c-c' dependents
        i = r['a_a']
        self.assertEqual(len(i.dependents), 2)
        self.assertIn('b_b', i.dependents)
        self.assertIn('c_c', i.dependents)
        # verify that the 'b-b' has the 'd-d' dependent
        i = r['b_b']
        self.assertEqual(len(i.dependents), 1)
        self.assertIn('d_d', i.dependents)
        # verify that the 'c-c' has the 'd-d' dependent
        i = r['c_c']
        self.assertEqual(len(i.dependents), 1)
        self.assertIn('d_d', i.dependents)
        # verify that 'd-d' has no dependents
        i = r['d_d']
        self.assertEqual(len(i.dependents), 0)

    def test_for_missing_key(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-b'])
        with self.assertRaises(core.ReactorError):
            core._calculate_dependents(r)


class TestCircularDependecyChecking(unittest.TestCase):
    """Note that we test for circular dependencies using the _check_reactor()
    function, as it also sets up the dependencies (which we can check is called
    using a wrapped Mock.
    """

    def test_passes_with_no_circular_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        f2 = lambda c: c.a_a + 2
        add_compute_helper(r, 'c-c', f2, ['a-a'])
        f3 = lambda c: c.b_b + c.c_c
        add_compute_helper(r, 'd-d', f3, ['b-b', 'c-c'])
        with mock.patch.object(core, '_calculate_dependents',
                               wraps=core._calculate_dependents) \
                as _calc_dep, \
                mock.patch.object(core, '_check_circular_dependencies',
                                  wraps=core._check_circular_dependencies) \
                as _check_circ_dep:
            core._check_reactor(r)
            _calc_dep.assert_called_once_with(r)
            # just verify that it was called
            _check_circ_dep.assert_any_call(r)

    def test_finds_circular_dependency(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        f2 = lambda c: c.a_a + 2
        # this is the circular dependency
        add_compute_helper(r, 'c-c', f2, ['a-a', 'd-d'])
        f3 = lambda c: c.b_b + c.c_c
        add_compute_helper(r, 'd-d', f3, ['b-b', 'c-c'])
        with self.assertRaises(core.ReactorError):
            core._check_reactor(r)


class TestResolveItem(unittest.TestCase):

    def test_single_input(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        x = core._resolve_item(r['a_a'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.key, 'a_a')
        self.assertEqual(x.name, 'a-a')
        self.assertEqual(x.item, 1)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, [])
        self.assertEqual(x.persistent, True)

    def test_single_compute(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'b-b', f1, ['a-a'])
        core._check_reactor(r)
        x = core._resolve_item(r['b_b'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.COMPUTE)
        self.assertEqual(x.key, 'b_b')
        self.assertEqual(x.name, 'b-b')
        self.assertEqual(x.item, f1)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, ['a_a'])
        self.assertEqual(x.persistent, True)
        # also check that a-a got the dependent
        x = core._resolve_item(r['a_a'])
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.dependents, {'b_b'})

    def test_resolve_to_default(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        core._add_input(r, 'a-a', 2, predicates=[lambda: False])
        x = core._resolve_item(r['a_a'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.key, 'a_a')
        self.assertEqual(x.name, 'a-a')
        self.assertEqual(x.item, 1)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, [])
        self.assertEqual(x.persistent, True)

    def test_resolve_to_default_change_order(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 2, predicates=[lambda: False])
        core._add_input(r, 'a-a', 1)
        x = core._resolve_item(r['a_a'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.key, 'a_a')
        self.assertEqual(x.name, 'a-a')
        self.assertEqual(x.item, 1)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, [])
        self.assertEqual(x.persistent, True)

    def test_resolve_to_predicate_true(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 1)
        core._add_input(r, 'a-a', 2, predicates=[lambda: True])
        x = core._resolve_item(r['a_a'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.key, 'a_a')
        self.assertEqual(x.name, 'a-a')
        self.assertEqual(x.item, 2)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, [])
        self.assertEqual(x.persistent, True)

    def test_resolve_to_predicate_true_change_order(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 2, predicates=[lambda: True])
        core._add_input(r, 'a-a', 1)
        x = core._resolve_item(r['a_a'])
        self.assertIsInstance(x, core.ResolvedItem)
        self.assertEqual(x.type_, core.Type.INPUT)
        self.assertEqual(x.key, 'a_a')
        self.assertEqual(x.name, 'a-a')
        self.assertEqual(x.item, 2)
        self.assertEqual(x.dependents, set())
        self.assertEqual(x.dependencies, [])
        self.assertEqual(x.persistent, True)

    def test_predicate_raises_exception(self):
        r = collections.OrderedDict()

        def raiser():
            raise Exception("hello")

        core._add_input(r, 'a-a', 2, predicates=[raiser])
        core._add_input(r, 'a-a', 1)
        with self.assertRaises(core.AbortExecution):
            core._resolve_item(r['a_a'])

    def test_predicate_only_that_is_false_returns_none(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a-a', 2, predicates=[lambda: False])
        self.assertIsNone(core._resolve_item(r['a_a']))

    def test_predicate_picks_correct_depenencies_and_persistent(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        core._add_input(r, 'b', 2)
        f1 = lambda c: c.a_a + 1
        add_compute_helper(r, 'c', f1, ['a'], persistent=False)
        f2 = lambda c: c.a_a + 2
        add_compute_helper(r, 'c', f2, ['b'], predicates=[lambda: False])
        x = core._resolve_item(r['c'])
        self.assertEqual(x.item, f1)
        self.assertEqual(x.dependencies, ['a'])
        self.assertEqual(x.persistent, False)


class TestProcessItem(unittest.TestCase):

    @staticmethod
    def context_fn(arg):
        return arg

    def test_process_input_value(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        i = core._resolve_item(r['a'])
        v = core._process_item(i, TestProcessItem.context_fn)
        self.assertEqual(v, 1)

    def test_process_input_function(self):
        r = collections.OrderedDict()
        f = lambda: 2
        core._add_input(r, 'a', lambda: f)
        i = core._resolve_item(r['a'])
        v = core._process_item(i, TestProcessItem.context_fn)
        self.assertEqual(v, 2)

    def test_process_compute_with_dependencies(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        f1 = lambda c: c
        add_compute_helper(r, 'b', f1, ['a'])
        i = core._resolve_item(r['b'])
        v = core._process_item(i, TestProcessItem.context_fn)
        self.assertEqual(v, ['a'])

    def test_process_raises_abort_function(self):
        r = collections.OrderedDict()

        def f():
            raise core.AbortFunction("aborted function")

        core._add_input(r, 'a', f)
        i = core._resolve_item(r['a'])
        with self.assertRaises(core.AbortFunction) as e:
            core._process_item(i, TestProcessItem.context_fn)
        self.assertEqual(str(e.exception), "aborted function")

    def test_process_raises_abort_execution(self):
        r = collections.OrderedDict()

        def f():
            raise core.AbortExecution("aborted execution")

        core._add_input(r, 'a', f)
        i = core._resolve_item(r['a'])
        with self.assertRaises(core.AbortExecution) as e:
            core._process_item(i, TestProcessItem.context_fn)
        self.assertEqual(str(e.exception), "aborted execution")

    def test_process_raises_other_exception(self):
        r = collections.OrderedDict()

        class CustomException(Exception):
            pass

        def f():
            raise CustomException("aborted custom")

        core._add_input(r, 'a', f)
        i = core._resolve_item(r['a'])
        with self.assertRaises(core.AbortExecution) as e:
            core._process_item(i, TestProcessItem.context_fn)
        self.assertTrue("aborted custom" in str(e.exception))

    def test_process_detects_invalid_type(self):
        i = core.ResolvedItem(None, 'a', 'a', 1, [], set(), True)
        with self.assertRaises(core.AbortExecution) as e:
            core._process_item(i, TestProcessItem.context_fn)
        self.assertTrue("Got unexpected type: None" in str(e.exception))


class TestFindUnprocessedDependencies(unittest.TestCase):

    def test_find_unprocessed_dependencies(self):
        i = core.ResolvedItem(core.Type.INPUT, 'a', 'a', 1, [],
                              {'a', 'b', 'c', 'd', 'e', 'f', 'g'},
                              True)
        processed = {'b', 'd', 'g'}
        result = list(core._find_unprocessed_dependencies(processed, i))
        self.assertEqual(len(result), 4)
        self.assertIn('a', result)
        self.assertIn('c', result)
        self.assertIn('e', result)
        self.assertIn('f', result)


class TestRun(unittest.TestCase):

    @staticmethod
    def getter(ctxt, l):
        return {k: v for k, v in ctxt.items() if k in l}

    @staticmethod
    def setter(ctxt, k, v):
        ctxt[k] = v

    @staticmethod
    def true(*args):
        return True

    def test_run_using_global(self):
        with mock.patch.object(core, '__reactor__', new={}) as r, \
                mock.patch.object(core, '_run') as _run:
            core.run()
            _run.assert_called_once_with({})

    def test_simple_run(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        f1 = lambda c: c['a'] + 1
        add_compute_helper(r, 'b', f1, ['a'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        core._run(r, TestRun.true, getter, setter)
        self.assertEqual(ctxt['a'], 1)
        self.assertEqual(ctxt['b'], 2)

    def test_more_complex(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        core._add_input(r, 'b', 2)
        core._add_input(r, 'c', 3)
        f1 = lambda c: c['a'] + 10
        f2 = lambda c: c['d'] * c['b']
        # Note this is to force a backtrack (i.e. using 'a' here) as it forces
        # f3 ('g') to be looked at early, which then causes 'b', etc to be
        # done.
        f3 = lambda c: c['e'] + c['c'] + c['a'] + 100
        out = None

        def f4(c):
            nonlocal out
            out = c['f']

        add_compute_helper(r, 'd', f1, ['a'])
        add_compute_helper(r, 'e', f2, ['d', 'b'])
        add_compute_helper(r, 'f', f3, ['e', 'c', 'a'])
        add_output_helper(r, 'g', f4, ['f'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        core._run(r, TestRun.true, getter, setter)
        self.assertEqual(ctxt['d'], 11)
        self.assertEqual(ctxt['e'], 22)
        self.assertEqual(ctxt['f'], 22 + 3 + 1 + 100)
        self.assertEqual(out, ctxt['f'])

    def test_abort_function(self):
        # test that a compute function can be aborted and stop the chain
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)

        def f1(c):
            raise core.AbortFunction()

        f2 = lambda c: 2
        add_compute_helper(r, 'b', f1, ['a'])
        add_compute_helper(r, 'c', f2, ['b'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        core._run(r, TestRun.true, getter, setter)
        self.assertEqual(ctxt['a'], 1)
        self.assertEqual(ctxt['b'], None)
        self.assertNotIn('c', ctxt)

    def test_abort_output(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)

        def f1(c):
            raise core.AbortFunction()

        add_output_helper(r, 'b', f1, ['a'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        core._run(r, TestRun.true, getter, setter)
        self.assertEqual(ctxt['a'], 1)
        self.assertNotIn('b', ctxt)

    def test_abort_execution(self):
        r = collections.OrderedDict()

        def f1():
            raise core.AbortExecution()

        core._add_input(r, 'a', f1)
        f2 = lambda c: 2
        add_compute_helper(r, 'b', f1, ['a'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        with self.assertRaises(core.AbortExecution):
            core._run(r, TestRun.true, getter, setter)
        self.assertNotIn('b', ctxt)

    def test_other_exception_causes_abort_execution(self):
        r = collections.OrderedDict()

        def f1():
            raise KeyError()

        core._add_input(r, 'a', f1)
        f2 = lambda c: 2
        add_compute_helper(r, 'b', f1, ['a'])
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        with self.assertRaises(core.AbortExecution) as e:
            core._run(r, TestRun.true, getter, setter)
        print(str(e.exception))
        self.assertNotIn('b', ctxt)

    def test_break_process_to_raise_weirdness(self):
        r = collections.OrderedDict()
        core._add_input(r, 'a', 1)
        ctxt = {}
        getter = functools.partial(TestRun.getter, ctxt)
        setter = functools.partial(TestRun.setter, ctxt)
        with mock.patch.object(core, '_process_item') as pi, \
                self.assertRaises(core.AbortExecution) as e:
            pi.side_effect = KeyError('foo')
            core._run(r, TestRun.true, getter, setter)
        self.assertIn('Weirdness:', str(e.exception))
        self.assertNotIn('a', ctxt)









