import pytest
from .. import JSONSchema, SchemaValidationError
from .. import validators as val


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
    root = JSONSchema(definition_schema)
    assert len(root._registry) == 11


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
    root = JSONSchema(circular_schema)
    assert isinstance(root.validators[0], val.RefValidator)
    assert isinstance(root.children[0].validators[0], val.AnyOfValidator)
