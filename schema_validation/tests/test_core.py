import pytest
from .. import Schema, SchemaValidationError, core


@pytest.fixture
def definition_schema():
    return {
        '$ref': '#/definitions/TopLevel',
        'definitions': {
            'TopLevel': {
                'anyOf': [
                    {'$ref': '#/definitions/Chart'},
                    {'$ref': '#/definitions/LayeredChart'},
                    {'$ref': '#/definitions/FacetedChart'}
                ]
            },
            'Chart': {'type': 'object', 'properties': {'a': {'type': 'string'}}},
            'LayeredChart': {'type': 'object', 'properties': {'a': {'type': 'integer'}}},
            'FacetedChart': {'type': 'object', 'properties': {'a': {'type': 'number'}}},
        }
    }


def test_definition_schema(definition_schema):
    root = Schema(definition_schema)
    assert len(root._registry) == 11


def generate_simple_schemas():
    yield ({'type': 'integer'}, [core.IntegerTypeValidator])
    yield ({'type': 'number'}, [core.NumberTypeValidator])
    yield ({'type': 'string'}, [core.StringTypeValidator])
    yield ({'type': 'null'}, [core.NullTypeValidator])
    yield ({'type': 'array'}, [core.ArrayValidator])
    yield ({'type': 'object'}, [core.ObjectValidator])
    yield ({'type': ['integer', 'number', 'string']}, [core.MultiTypeValidator])
    yield ({'properties': {'foo': {'type': 'string'}}}, [core.ObjectValidator])
    yield ({'additionalProperties': {'type': 'string'}}, [core.ObjectValidator])
    yield ({'enum': ['hello'], 'type': 'string'}, [core.EnumValidator,
                                                   core.StringTypeValidator])
    yield ({'enum': [0, 1], 'type': 'integer'}, [core.EnumValidator,
                                                 core.IntegerTypeValidator])
    yield ({'enum': [0, 1], 'type': 'number'}, [core.EnumValidator,
                                                core.NumberTypeValidator])
    yield ({'enum': [True], 'type': 'boolean'}, [core.EnumValidator,
                                                 core.BooleanTypeValidator])
    yield ({'enum': [None], 'type': 'null'}, [core.EnumValidator,
                                              core.NullTypeValidator])
    yield ({'enum': ['hello', None, 2]}, [core.EnumValidator])
    yield ({'description': 'foo'}, [])
    yield ({}, [])
    yield ({'$ref': '#/definitions/blah',
            'definitions': {'blah': {'type': 'string'}}},
           [core.RefValidator])
    yield({'anyOf': [{'type': 'integer'}, {'type': 'string'}]},
          [core.AnyOfValidator])


@pytest.mark.parametrize('schema, vclasses', generate_simple_schemas())
def test_simple_schemas(schema, vclasses):
    root = Schema(schema)
    assert len(root.validators) == len(vclasses)
    for v in root.validators:
        assert isinstance(v, tuple(vclasses))

    schema['$schema'] = 'http://foo.com/schema.json/#'
    schema['description'] = 'this is a description'
    root = Schema(schema)
    assert len(root.validators) == len(vclasses)
    for v in root.validators:
        assert isinstance(v, tuple(vclasses))


@pytest.fixture
def circular_schema():
    return{
        '$ref': '#/definitions/Obj',
        'definitions': {
            'Obj': {'anyOf': [{'type': 'integer'},
                              {'type': 'array', 'items': {'$ref': '#/definitions/Obj'}}]}
        }
    }


def test_circular_schema(circular_schema):
    root = Schema(circular_schema)
    assert isinstance(root.validators[0], core.RefValidator)
    assert isinstance(root.children[0].validators[0], core.AnyOfValidator)


def schemas_for_validation():
    yield ({"type": "number"},
           [1, 2.5], [True, None, 'hello'])
    yield ({"type": "integer"},
           [1, 2.0], [True, None, 'hello', 2.5])
    yield ({"type": "string"},
           ["", 'hello'], [True, None, 1, 2.5])
    yield ({"type": "boolean"},
           [True, False], ['hello', None, 1, 2.5])
    yield ({"type": "null"},
           [None], ['hello', True, 1, 2.5])
    yield ({"type": "array", 'items': {}},
           [[1,'hello'], [None, True]], [1, 'hello'])
    yield ({"type": "array", 'items': {'type': 'number'}},
           [[1,2], [0.1, 2.5]], [[2.0, 'hello'], [1, None]])
    yield ({"enum": [5, "hello", None, False]},
           [5, "hello", None, False], [2, 'blah', True])
    yield ({"type": "string", "enum": ['a', 'b', 'c']},
           ['a', 'b', 'c'], [2, 'blah', True])
    yield ({"type": "number", "minimum": 0, "maximum": 1},
           [0, 0.5, 1], [-1, 2])
    yield ({"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 1},
           [0.01, 0.5, 0.99], [0, 1])
    yield ({"type": "string", 'minLength': 2, 'maxLength': 5},
           ["12", "123", "12345"], ["", "1", "123456"])
    # TODO: object, ref, anyOf, oneOf, allOf, not, compound


@pytest.mark.parametrize('schema,valid,invalid', schemas_for_validation())
def test_simple_validation(schema, valid, invalid):
    schemaobj = Schema(schema)

    for value in valid:
        schemaobj.validate(value)

    for value in invalid:
        with pytest.raises(SchemaValidationError):
            schemaobj.validate(value)
