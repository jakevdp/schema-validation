import os
import json

import pytest

from ... import JSONSchema
from .. import iter_schemas_with_names, load_schema

num_schemas = {'vega-v3.0.7.json': 631,
               'vega-lite-v1.2.json': 309,
               'vega-lite-v2.0.json': 645}

num_definitions = {'vega-v3.0.7.json': 106,
                   'vega-lite-v1.2.json': 54,
                   'vega-lite-v2.0.json': 150}


@pytest.mark.filterwarnings('ignore:Unused')
@pytest.mark.parametrize('name,schema', iter_schemas_with_names())
def test_full_schemas(name, schema):
    root = JSONSchema(schema)
    assert len(root._registry) == num_schemas.get(name, None)
    assert len(root._definitions) == num_definitions.get(name, None)


@pytest.mark.filterwarnings('ignore:Unused')
def test_schema_validation():
    schema = JSONSchema(load_schema('vega-lite-v2.0.json'))

    vega_lite_bar = {
      "$schema": "https://vega.github.io/schema/vega-lite/v2.json",
      "description": "A simple bar chart with embedded data.",
      "data": {
        "values": [
          {"a": "A","b": 28}, {"a": "B","b": 55}, {"a": "C","b": 43},
          {"a": "D","b": 91}, {"a": "E","b": 81}, {"a": "F","b": 53},
          {"a": "G","b": 19}, {"a": "H","b": 87}, {"a": "I","b": 52}
        ]
      },
      "mark": "bar",
      "encoding": {
        "x": {"field": "a", "type": "ordinal"},
        "y": {"field": "b", "type": "quantitative"}
      }
    }
    schema.validate(vega_lite_bar)

    vega_lite_github_punchcard = {
      "$schema": "https://vega.github.io/schema/vega-lite/v2.json",
      "data": { "url": "data/github.csv"},
      "mark": "circle",
      "encoding": {
        "y": {
          "field": "time",
          "type": "ordinal",
          "timeUnit": "day"
        },
        "x": {
          "field": "time",
          "type": "ordinal",
          "timeUnit": "hours"
        },
        "size": {
          "field": "count",
          "type": "quantitative",
          "aggregate": "sum"
        }
      }
    }
    schema.validate(vega_lite_github_punchcard)
