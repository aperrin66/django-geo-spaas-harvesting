# pylint: disable=protected-access
"""Tests for the argument classes"""
import unittest
import unittest.mock as mock
from datetime import datetime, timezone as tz

import shapely.errors
import shapely.geometry

import geospaas_harvesting.arguments as arguments


class ArgumentParserTestCase(unittest.TestCase):
    """Tests for the ArgumentParser class"""

    def test_arg_parser_instanciation(self):
        """Test instanciation"""
        argument = arguments.AnyArgument('foo')
        arg_parser = arguments.ArgumentParser([argument])
        self.assertDictEqual(arg_parser.arguments, {'foo': argument})

    def test_arg_parser_instanciation_error(self):
        """A ValueError should be raised when ArgumentParser is not
        initialized with arguments
        """
        with self.assertRaises(ValueError):
            arguments.ArgumentParser(['foo'])

    def test_parse(self):
        """Test parsing an argument"""
        argument = arguments.AnyArgument('foo')
        argument.add_child(arguments.AnyArgument('baz', default='qux'))
        arg_parser = arguments.ArgumentParser([argument])
        self.assertDictEqual(
            arg_parser.parse({'foo': 'bar'}),
            {'foo': 'bar', 'baz': 'qux'})

    def test_parse_required_error(self):
        """An error must be raised if a required argument is missing"""
        arg = arguments.AnyArgument('foo', required=True)
        with self.assertRaises(ValueError):
            arguments.ArgumentParser([arg]).parse({})

    def test_strict_parse_error(self):
        """In strict mode, only known arguments are allowed"""
        arg_parser = arguments.ArgumentParser([arguments.AnyArgument('foo')], strict=True)
        with self.assertRaises(ValueError):
            arg_parser.parse({'foo': 'bar', 'baz': 'qux'})

class ArgumentTestCase(unittest.TestCase):
    """Tests for the Argument base class"""

    def test_abstract_parse(self):
        """The parse() method should not be defined in the base
        Argument class
        """
        with self.assertRaises(NotImplementedError):
            arguments.Argument('foo').parse(mock.Mock())

    def test_equality(self):
        """Test the equality operator between argument objects"""
        self.assertEqual(arguments.Argument('foo'), arguments.Argument('foo'))
        self.assertNotEqual(arguments.Argument('foo'), arguments.Argument('bar'))
        self.assertNotEqual(arguments.Argument('foo', required=True),
                            arguments.Argument('foo', required=False))

    def test_add_child(self):
        """Test adding a child to an argument"""
        parent = arguments.Argument('foo')
        child = arguments.Argument('bar')
        parent.add_child(child)
        self.assertIn(child, parent.children)
        self.assertEqual(child.parent, parent)

    def test_set_parent(self):
        """Test setting the parent for an argument"""
        parent = arguments.Argument('foo')
        child = arguments.Argument('bar')
        child._set_parent(parent)
        self.assertEqual(child.parent, parent)


class AnyArgumentTestCase(unittest.TestCase):
    """Tests for the AnyArgument class"""

    def test_parse(self):
        """parse() should just return the given value"""
        self.assertEqual(arguments.AnyArgument('foo').parse('bar'), 'bar')


class BooleanArgumentTestCase(unittest.TestCase):
    """Tests for the BooleanArgument class"""

    def test_parse(self):
        """A boolean argument should be an explicit boolean"""
        arg = arguments.BooleanArgument('foo')
        self.assertIs(arg.parse(True), True)
        self.assertIs(arg.parse(False), False)
        for wrong_value in ['', 'a', 0, 1, [], ['a'], {}]:
            with self.subTest(f"{wrong_value} should not be a valid boolean argument"):
                with self.assertRaises(ValueError):
                    arg.parse(wrong_value)


class ChoiceArgumentTestCase(unittest.TestCase):
    """Tests for the ChoiceArgument class"""

    def test_parse(self):
        """Test value validation"""
        arg = arguments.ChoiceArgument('foo', valid_options=['bar', 'baz'], default='baz')
        self.assertEqual(arg.parse('bar'), 'bar')
        with self.assertRaises(ValueError):
            arg.parse('qux')

    def test_equality(self):
        """Test the equality operator"""
        self.assertEqual(arguments.ChoiceArgument('foo', valid_options=['bar']),
                         arguments.ChoiceArgument('foo', valid_options=['bar']))
        self.assertNotEqual(arguments.ChoiceArgument('foo', valid_options=['bar']),
                            arguments.ChoiceArgument('baz', valid_options=['bar']))
        self.assertNotEqual(arguments.ChoiceArgument('foo', valid_options=['bar']),
                            arguments.ChoiceArgument('foo', valid_options=['baz']))


class DatetimeArgumentTestCase(unittest.TestCase):
    """Tests for the DatetimeArgument class"""

    def test_parse(self):
        """Test parsing datetimes"""
        arg = arguments.DatetimeArgument('foo')
        self.assertEqual(arg.parse('2023-01-01T00:00:00Z'), datetime(2023, 1, 1, tzinfo=tz.utc))
        self.assertEqual(arg.parse('2023-01-01'), datetime(2023, 1, 1, tzinfo=tz.utc))
        self.assertIsNone(arg.parse(None))


class DictArgumentTestCase(unittest.TestCase):
    """Tests for the DictArgument class"""

    def test_parse(self):
        """Test data validation"""
        arg = arguments.DictArgument(name='dict_arg', valid_keys=['foo'])

        self.assertEqual(arg.parse({'foo': 'bar'}), {'foo': 'bar'})

        with self.assertRaises(ValueError):
            arg.parse('foo')

        with self.assertRaises(ValueError):
            arg.parse({'baz': 'qux'})

    def test_eq(self):
        """Test equality between dict arguments"""
        self.assertEqual(
            arguments.DictArgument(name='foo', valid_keys=['bar']),
            arguments.DictArgument(name='foo', valid_keys=['bar']))
        self.assertNotEqual(
            arguments.DictArgument(name='foo', valid_keys=['bar']),
            arguments.DictArgument(name='foo', valid_keys=['baz']))


class IntegerArgumentTestCase(unittest.TestCase):
    """Tests for the IntegerArgument class"""

    def test_parse(self):
        """Test integer validation"""
        arg = arguments.IntegerArgument(name='foo', min_value=1, max_value=5)
        self.assertEqual(arg.parse(1), 1)
        self.assertEqual(arg.parse(2), 2)
        self.assertEqual(arg.parse(5), 5)
        with self.assertRaises(ValueError):
            arg.parse('0')
        with self.assertRaises(ValueError):
            arg.parse(0)
        with self.assertRaises(ValueError):
            arg.parse(10)

    def test_eq(self):
        """Test integer argument equality"""
        self.assertEqual(arguments.IntegerArgument(name='foo', min_value=1, max_value=5),
                         arguments.IntegerArgument(name='foo', min_value=1, max_value=5))
        self.assertNotEqual(arguments.IntegerArgument(name='foo', min_value=1, max_value=5),
                            arguments.IntegerArgument(name='foo', min_value=1, max_value=6))


class ListArgumentTestCase(unittest.TestCase):
    """Tests for the ListArgument class"""

    def test_parse(self):
        """Test list argument validation"""
        arg = arguments.ListArgument(name='foo')
        self.assertEqual(arg.parse([1, 2]), [1, 2])
        with self.assertRaises(ValueError):
            arg.parse(1)


class PathArgumentTestCase(unittest.TestCase):
    """Tests for the PathArgument class"""

    def test_is_path(self):
        """Test checking that a string represents a path"""
        arg = arguments.PathArgument(name='foo')
        self.assertTrue(arg.is_path('/bar'))
        self.assertTrue(arg.is_path('/bar/'))
        self.assertTrue(arg.is_path('/bar/baz'))
        self.assertTrue(arg.is_path('/bar/baz/'))
        self.assertTrue(arg.is_path('./bar'))
        self.assertTrue(arg.is_path('../bar'))
        self.assertFalse(arg.is_path('bar'))
        self.assertFalse(arg.is_path('bar/baz'))

    def test_validate(self):
        """Test path validation"""
        arg = arguments.PathArgument(name='foo', valid_options=['/foo'])
        self.assertEqual(arg.parse('/foo'), '/foo')
        self.assertEqual(arg.parse('/foo/bar'), '/foo/bar')
        with self.assertRaises(ValueError):
            arg.parse('/baz')
        with self.assertRaises(ValueError):
            arg.parse('1')


class StringArgumentTestCase(unittest.TestCase):
    """Tests for the StringArgument class"""

    def test_parse(self):
        """Test string validation"""
        arg = arguments.StringArgument(name='foo', regex='^bar.*$')
        self.assertEqual(arg.parse('bar baz'), 'bar baz')
        with self.assertRaises(ValueError):
            arg.parse(1)
        with self.assertRaises(ValueError):
            arg.parse('qux')

    def test_eq(self):
        """Test equality operator between StringArgument objects"""
        self.assertEqual(arguments.StringArgument(name='foo', regex='^bar.*$'),
                         arguments.StringArgument(name='foo', regex='^bar.*$'))
        self.assertNotEqual(arguments.StringArgument(name='foo', regex='^bar.*$'),
                            arguments.StringArgument(name='foo', regex='^baz.*$'))


class WKTArgumentTestCase(unittest.TestCase):
    """Tests for the WKTArgument class"""

    def test_parse(self):
        """Test WKT parsing"""
        arg = arguments.WKTArgument('foo', geometry_types=[shapely.geometry.Point])
        self.assertEqual(arg.parse('POINT(1 2)'), shapely.geometry.Point((1, 2)))
        # not WKT
        with self.assertRaises(shapely.errors.WKTReadingError), self.assertLogs():
            arg.parse('bar')
        # wrong geometry type
        with self.assertRaises(ValueError):
            arg.parse('POLYGON((1 2, 2 3, 3 4, 1 2))')

    def test_eq(self):
        """Test equality between WKTArgument objects"""
        self.assertEqual(arguments.WKTArgument('foo', geometry_types=[shapely.geometry.Point]),
                         arguments.WKTArgument('foo', geometry_types=[shapely.geometry.Point]))
        self.assertNotEqual(arguments.WKTArgument('foo', geometry_types=[shapely.geometry.Point]),
                            arguments.WKTArgument('foo', geometry_types=[shapely.geometry.Polygon]))
