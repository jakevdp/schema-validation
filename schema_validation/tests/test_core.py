import pytest
from .. import Schema, core


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
