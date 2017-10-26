"""
Design thoughts:

Attributes

- validators are a list of zero or more Validators, built from parts of the schema
- parents are a physically storedlist of zero or more parent Schemas
- children are a dynamically calculated list of zero or more child schemas (with validators
  knowing how to find children)
- each has a root attribute pointing to the root Schema
- root Schema has a registry of instantiated Schemas, mapped from their schema hash,
  such that if a schema appears multiple times, its multiple parents will be tracked.
- result is a graph that may or may not be fully or partially cyclic.
"""

import warnings
import itertools

from .utils import hash_schema, nested_dict_repr


class Schema(object):
    def __init__(self, schema, root=None):
        self._registry = {}
        self.schema = schema
        self.root = root or self
        self.validators = self._initialize_validators()
        self.parents = []

        # We need setup to finish entirely before recursively creating children
        # and so we call it only for the root object.
        if self is self.root:
            self._registry[hash_schema(self.schema)] = self
            self._recursively_create_children()

    @property
    def registry(self):
        """Registry of instantiated Schema objects"""
        return self.root._registry

    def _initialize_validators(self):
        # key = hash_schema(schema)
        validator_classes = [cls for cls in Validator.__subclasses__()
                             if cls._matches(self.schema)]
        validators = []

        used_keys = {'definitions', 'description', 'title', '$schema'}
        for cls in validator_classes:
            cls_schema = {key:val for key, val in self.schema.items()
                          if key in cls.recognized_keys}
            used_keys |= cls_schema.keys()
            validators.append(cls(cls_schema, parent=self))
        unused = self.schema.keys() - used_keys
        if unused:
            warnings.warn("Unused keys {0} in {1}"
                          "".format(unused, validators))
        return validators

    def _recursively_create_children(self):
        seen = set()
        def crawl(obj):
            for child in obj.children:
                hsh = hash_schema(child.schema)
                #child.parents.add(obj)
                if hsh not in seen:
                    seen.add(hsh)
                    crawl(child)
        crawl(self)

    def initialize_child(self, schema, parent=None):
        key = hash_schema(schema)
        if key not in self.registry:
            self.registry[key] = Schema(schema, root=self.root)
        obj = self.registry[key]
        if self not in obj.parents:
            obj.parents.append(self)
        return obj

    @property
    def children(self):
        schemas = itertools.chain(*(v.children for v in self.validators))
        return [self.initialize_child(schema) for schema in schemas]

    def __repr__(self):
        return "Schema({0})".format(self.validators)


class Validator(object):
    def __init__(self, schema, parent):
        self.schema = schema
        self.parent = parent

        unrecognized = set(schema.keys()) - set(self.recognized_keys)
        if unrecognized:
            warnings.warn('Unrecognized keys {0} in class {1}'
                          ''.format(unrecognized, self.__class__.__name__))

    @classmethod
    def _matches(cls, schema):
        return False

    @property
    def children(self):
        return []

    def __repr__(self):
        if len(self.schema) > 3:
            args = ', '.join(sorted(self.schema.keys())[:3]) + '...'
        else:
            args = ', '.join(sorted(self.schema.keys()))
        return "{0}({1})".format(self.__class__.__name__, args)


class ObjectValidator(Validator):
    recognized_keys = {'type', 'properties', 'additionalProperties',
                       'patternProperties', 'required'}
    # TODO: handle pattern properties
    @classmethod
    def _matches(cls, schema):
        return (schema.get('type', None) == 'object'
                 or 'properties' in schema
                 or 'additionalProperties' in schema)

    @property
    def children(self):
        props = list(self.schema.get('properties', {}).values())
        props += list(self.schema.get('patternProperties', {}).values())
        addprops = self.schema.get('additionalProperties', None)
        if isinstance(addprops, dict):
            props.append(addprops)
        return props


class ArrayValidator(Validator):
    recognized_keys = {'type', 'items', 'minItems', 'maxItems', 'numItems'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'array' or 'items' in schema

    @property
    def children(self):
        if 'items' in self.schema:
            return [self.schema['items']]
        else:
            return []


class NumberTypeValidator(Validator):
    recognized_keys = {'type', 'minimum', 'maximum', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'number'


class IntegerTypeValidator(Validator):
    recognized_keys = {'type', 'mimimum', 'maximum', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'integer'


class StringTypeValidator(Validator):
    recognized_keys = {'type', 'pattern', 'format',
                       'minLength', 'maxLength', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'string'


class NullTypeValidator(Validator):
    recognized_keys = {'type'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'null'


class BooleanTypeValidator(Validator):
    recognized_keys = {'type', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'boolean'


class EnumValidator(Validator):
    recognized_keys = {'enum', 'default'}
    @classmethod
    def _matches(cls, schema):
        return 'enum' in schema


class MultiTypeValidator(Validator):
    recognized_keys = {'type', 'minimum', 'maximum'}
    @classmethod
    def _matches(cls, schema):
        return isinstance(schema.get('type', None), list)


class RefValidator(Validator):
    recognized_keys = {'$ref'}

    @classmethod
    def _matches(cls, schema):
        return '$ref' in schema

    @property
    def children(self):
        keys = self.schema['$ref'].split('/')
        if keys[0] != '#':
            raise ValueError("$ref = {0} not recognized".format(self.schema['$ref']))
        refschema = self.parent.root.schema
        for key in keys[1:]:
            refschema = refschema[key]
        return [refschema]

    @property
    def name(self):
        return self.schema['$ref']

    def __repr__(self):
        return "RefValidator('{0}')".format(self.name)


class AnyOfValidator(Validator):
    recognized_keys = {'anyOf'}
    @classmethod
    def _matches(cls, schema):
        return 'anyOf' in schema

    @property
    def children(self):
        return self.schema['anyOf']


class OneOfValidator(Validator):
    recognized_keys = {'oneOf'}
    @classmethod
    def _matches(cls, schema):
        return 'oneOf' in schema

    @property
    def children(self):
        return self.schema['oneOf']


class AllOfValidator(Validator):
    recognized_keys = {'allOf'}
    @classmethod
    def _matches(cls, schema):
        return 'allOf' in schema

    @property
    def children(self):
        return self.schema['allOf']


class NotValidator(Validator):
    recognized_keys = {'not'}
    @classmethod
    def _matches(cls, schema):
        return 'not' in schema

    @property
    def children(self):
        return [self.schema['not']]
