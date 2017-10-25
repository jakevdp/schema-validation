import random
import pytest
from ..utils import hash_schema


def generate_schemas():
    yield 4
    yield 3.14
    yield 'foo'
    yield None
    yield {'a': 1, 'b': 2}
    yield [1, 2, 3]
    yield (1, 2, 3)
    yield {
        'a': {
            'key': [1, 2, 3],
            'val': ['a', 'b', 'c']
            },
        'b': [{}, {'name': 'bob', 'age': 31}],
        'c': (1, 2, 3)
    }
    yield {
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


def scramble(val):
    # scramble the order in which the dict is defined
    if isinstance(val, dict):
        L = [(k, scramble(v)) for k, v in val.items()]
        random.shuffle(L)
        return dict(L)
    elif isinstance(val, tuple):
        return tuple(map(scramble, val))
    elif isinstance(val, list):
        return list(map(scramble, val))
    else:
        return val


@pytest.mark.parametrize('schema', generate_schemas())
def test_hash_schema(schema):
    """Test that schemas compile correctly, even when order is changed"""
    hsh = hash_schema(schema)
    assert all(hash_schema(scramble(schema)) == hsh for i in range(10))
