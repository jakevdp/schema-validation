import os
import json

import pytest

from .. import Schema


def iter_schemas():
    schema_dir = os.path.join(os.path.dirname(__file__), '..', 'schemas')
    for schema in os.listdir(schema_dir):
        if schema.endswith('json'):
            with open(os.path.join(schema_dir, schema)) as f:
                yield json.load(f)


@pytest.mark.parametrize('schema', iter_schemas())
def test_full_schemas(schema):
    # smoketest
    # TODO: add more complete tests here
    root = Schema(schema)
