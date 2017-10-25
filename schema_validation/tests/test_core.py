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


def generate_simple_schemas():
    yield ({'type': 'integer'}, core.IntegerTypeSchema)
    yield ({'type': 'number'}, core.NumberTypeSchema)
    yield ({'type': 'string'}, core.StringTypeSchema)
    yield ({'type': 'null'}, core.NullTypeSchema)
    yield ({'type': 'array'}, core.ArraySchema)
    yield ({'type': 'object'}, core.ObjectSchema)
    yield ({'type': ['integer', 'number', 'string']}, core.MultiTypeSchema)
    yield ({'properties': {'foo': {'type': 'string'}}}, core.ObjectSchema)
    yield ({'additionalProperties': {'type': 'string'}}, core.ObjectSchema)
    yield ({'enum': ['hello'], 'type': 'string'}, core.EnumSchema)
    yield ({'enum': [0, 1], 'type': 'integer'}, core.EnumSchema)
    yield ({'enum': [0, 1], 'type': 'number'}, core.EnumSchema)
    yield ({'enum': [True], 'type': 'boolean'}, core.EnumSchema)
    yield ({'enum': [None], 'type': 'null'}, core.EnumSchema)
    yield ({'enum': ['hello', None, 2]}, core.EnumSchema)
    yield ({'description': 'foo'}, core.EmptySchema)
    yield ({}, core.EmptySchema)
    yield ({'$ref': '#/definitions/blah',
            'definitions': {'blah': {'type': 'string'}}},
           core.RefSchema)
    yield({'anyOf': [{'type': 'integer'}, {'type': 'string'}]},
          core.AnyOfSchema)


def test_definition_schema(definition_schema):
    root = Schema(definition_schema)
    assert len(root._defined_schemas) == 11


@pytest.mark.parametrize('schema, cls', generate_simple_schemas())
def test_simple_schemas(schema, cls):
    root = Schema(schema)
    assert isinstance(root.tree, cls)

    schema['$schema'] = 'http://foo.com/schema.json/#'
    schema['description'] = 'this is a description'
    root = Schema(schema)
    assert isinstance(root.tree, cls)
