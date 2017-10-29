import os
import json

import pytest

from ... import Schema, schemas


@pytest.mark.parametrize('schema', schemas.iter_schemas())
def test_full_schemas(schema):
    # smoketest
    # TODO: add more complete tests here
    root = Schema(schema)


def test_schema_validation():
    schema = Schema(schemas.load_schema('vega-lite-v2.0.json'))

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
