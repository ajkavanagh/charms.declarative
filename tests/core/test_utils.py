import unittest

import charms.declarative.core.utils as u


class TestUtils(unittest.TestCase):

    def test_maybe_format_key_valid(self):
        patterns = (
            ('a', 'a'),
            ('aa', 'aa'),
            ('a1', 'a1'),
            ('a_', 'a_'),
            ('_a', '_a'),
            ('a_a', 'a_a'),
            ('-', '_'),
            ('--', '__'),
            ('a-', 'a_'),
            ('-a', '_a'),
            ('a-b', 'a_b'),
            ('a-b-c', 'a_b_c'),
            ('a-1', 'a_1'),
            ('the-attr', 'the_attr'),
            ('/', '__'),
            ('//', '____'),
            ('/the/path.conf', '__the__path_conf'),
            (r'\the\path.conf', '__the__path_conf'),
        )

        for p in patterns:
            self.assertEqual(u.maybe_format_key(p[0]), p[1])

    def test_maybe_format_key_invalid_patterns(self):
        patterns = (
            '$',
            '#',
            '"',
            "'",
            "0",
            "0a",
            "1234",
            "1_",
            "1/",
            '1\\',
        )

        for p in patterns:
            with self.assertRaises(AttributeError):
                u.maybe_format_key(p)
