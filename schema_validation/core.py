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
import math

from .utils import hash_schema, nested_dict_repr, isnumeric


class Schema(object):
    """Wrapper for a JSON schema

    Parameters
    ----------
    schema : dict
        a Schema dictionary

    Attributes
    ----------
    schema : dict
        the schema dictionary
    root : Schema object
        a pointer to the root schema
    validators : list
        a list of Validator classes for this level of the schema
    parents : list
        a list of parent objects to the current schema

    Notes
    -----
    The root Schema has a _registry attribute, which is a dictionary mapping
    unique hashes of each schema to a Schema object which wraps it. When the
    tree of schema objects is created, this registry is used to identify
    when two schemas are identical, both for efficiency and to detect
    cyclical schema definitions.

    Because of this, the ``parents`` attribute is able to point to all parents
    of each unique schema, even if it occurs multiple times in the schema tree.

    Each schema will match zero or more "validator" classes, which can be used
    to validate input.
    """
    def __init__(self, schema, **kwds):
        unrecognized_args = kwds.keys() - {'root'}
        if unrecognized_args:
            raise ValueError('Unrecognized arguments to Schema: {0}'
                             ''.format(unrecognized_args))
        self.schema = schema
        self.root = kwds.get('root', self)
        self.validators = Validator._initialize_validators(self)
        self.parents = []

        # We need setup to finish entirely before recursively creating children
        # and so we call it only for the root object.
        if self is self.root:
            self._registry = {}
            self._registry[hash_schema(self.schema)] = self
            self._recursively_create_children()

    @classmethod
    def from_file(cls, file):
        try:
            schema = json.load(file)
        except AttributeError:
            with open(file, 'r') as f:
                schema = json.load(f)
        return cls(schema)

    @property
    def registry(self):
        """Registry of instantiated Schema objects"""
        return self.root._registry

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

    def initialize_child(self, schema):
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

    def validate(self, obj):
        for validator in self.validators:
            validator.validate(obj)


class SchemaValidationError(Exception):
    pass


class Validator(object):
    def __init__(self, schema, parent):
        self.schema = schema
        self.parent = parent

        unrecognized = set(schema.keys()) - set(self.recognized_keys)
        if unrecognized:
            warnings.warn('Unrecognized keys {0} in class {1}'
                          ''.format(unrecognized, self.__class__.__name__))

    @classmethod
    def _initialize_validators(cls, obj):
        """
        Parameters
        ----------
        obj: Schema
            the Schema object for which the validators will be initialized
        """
        validator_classes = [cls for cls in cls.__subclasses__()
                             if cls._matches(obj.schema)]
        validators = []

        used_keys = {'definitions', 'description', 'title', '$schema'}
        for cls in validator_classes:
            cls_schema = {key:val for key, val in obj.schema.items()
                          if key in cls.recognized_keys}
            used_keys |= cls_schema.keys()
            validators.append(cls(cls_schema, parent=obj))
        unused = obj.schema.keys() - used_keys
        if unused:
            warnings.warn("Unused keys {0} in {1}"
                          "".format(unused, validators))
        return validators

    def init_child(self, schema):
        return self.parent.initialize_child(schema)

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

    def validate(self, value):
        raise NotImplementedError()


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

    def validate(self, obj):
        if not isinstance(obj, dict):
            raise SchemaValidationError("{0} is not of type='object'".format(obj))
        if not all(key in obj for key in self.get('required', [])):
            raise SchemaValidationError("{0} does not contain required keys {1}"
                                        "".format(obj, self.schema['required']))
        for key, val in obj.items:
            properties = self.schema.get('properties', {})
            patternProperties = self.schema.get('patternProperties', {})
            additionalProperties = self.schema.get('additionalProperties', True)
            if key in properties:
                self.init_child(properties[key]).validate(val)
            elif patternProperties:
                raise NotImplementedError('patternProperties validation')
            elif isinstance(additionalProperties, dict):
                self.parent.initialize_child(additionalProperties).validate(val)
            elif not additionalProperties:
                raise SchemaValidationError("{0} property {1} is invalid"
                                            "".format(obj, key))


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

    def validate(self, obj):
        if not isinstance(obj, list):
            raise SchemaValidationError()
        if 'minItems' in self.schema and len(obj) < self.schema['minItems']:
            raise SchemaValidationError()
        if 'maxItems' in self.schema and len(obj) > self.schema['maxItems']:
            raise SchemaValidationError()
        if 'numItems' in self.schema and len(obj) != self.schema['numItems']:
            raise SchemaValidationError()


class NumberTypeValidator(Validator):
    recognized_keys = {'type', 'minimum', 'maximum', 'default',
                       'exclusiveMinimum', 'exclusiveMaximum'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'number'

    def validate(self, obj):
        if not isnumeric(obj):
            raise SchemaValidationError("{0} is not a numeric type"
                                        "".format(obj))
        if 'minimum' in self.schema and obj < self.schema['minimum']:
            raise SchemaValidationError("{0} is less than minimum={1}"
                                        "".format(obj, self.schema['minimum']))
        if 'maximum' in self.schema and obj > self.schema['maximum']:
            raise SchemaValidationError("{0} is greater than maximum={1}"
                                        "".format(obj, self.schema['maximum']))
        if 'exclusiveMinimum' in self.schema and obj <= self.schema['exclusiveMinimum']:
            raise SchemaValidationError("{0} is less than exclusiveMinimum={1}"
                                        "".format(obj, self.schema['exclusiveMinimum']))
        if 'exclusiveMaximum' in self.schema and obj >= self.schema['exclusiveMaximum']:
            raise SchemaValidationError("{0} is greater than exclusiveMaximum={1}"
                                        "".format(obj, self.schema['exclusiveMaximum']))


class IntegerTypeValidator(Validator):
    recognized_keys = {'type', 'mimimum', 'maximum', 'default',
                       'exclusiveMinimum', 'exclusiveMaximum'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'integer'

    def validate(self, obj):
        if not isnumeric(obj):
            raise SchemaValidationError("{0} is not a numeric type"
                                        "".format(obj))
        if not int(obj) == obj:
            raise SchemaValidationError("{0} is not an integer".format(obj))
        if 'minimum' in self.schema and obj < self.schema['minimum']:
            raise SchemaValidationError("{0} is less than minimum={1}"
                                        "".format(obj, self.schema['minimum']))
        if 'maximum' in self.schema and obj > self.schema['maximum']:
            raise SchemaValidationError("{0} is greater than maximum={1}"
                                        "".format(obj, self.schema['maximum']))
        if 'exclusiveMinimum' in self.schema and obj <= self.schema['exclusiveMinimum']:
            raise SchemaValidationError("{0} is less than exclusiveMinimum={1}"
                                        "".format(obj, self.schema['exclusiveMinimum']))
        if 'exclusiveMaximum' in self.schema and obj >= self.schema['exclusiveMaximum']:
            raise SchemaValidationError("{0} is greater than exclusiveMaximum={1}"
                                        "".format(obj, self.schema['exclusiveMaximum']))


class StringTypeValidator(Validator):
    recognized_keys = {'type', 'pattern', 'format',
                       'minLength', 'maxLength', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'string'

    def validate(self, obj):
        if not isinstance(obj, str):
            raise SchemaValidationError("{0} is not a string".format(obj))
        if 'minLength' in self.schema and len(obj) < self.schema['minLength']:
            raise SchemaValidationError("{0} is shorter than minLength={1}"
                                        "".format(obj, self.schema['minLength']))
        if 'maxLength' in self.schema and len(obj) > self.schema['maxLength']:
            raise SchemaValidationError("{0} is longer than maxLength={1}"
                                        "".format(obj, self.schema['maxLength']))
        if 'pattern' in self.schema or 'format' in self.schema:
            warnings.warn("pattern and format not implemented in StringTypeValidator")


class NullTypeValidator(Validator):
    recognized_keys = {'type'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'null'

    def validate(self, obj):
        if obj is not None:
            raise SchemaValidationError()


class BooleanTypeValidator(Validator):
    recognized_keys = {'type', 'default'}
    @classmethod
    def _matches(cls, schema):
        return schema.get('type', None) == 'boolean'

    def validate(self, obj):
        if not isinstance(obj, bool):
            raise SchemaValidationError()


class EnumValidator(Validator):
    recognized_keys = {'enum', 'default'}
    @classmethod
    def _matches(cls, schema):
        return 'enum' in schema

    def validate(self, obj):
        print(obj, self.schema['enum'], obj in self.schema['enum'])
        if obj not in self.schema['enum']:
            raise SchemaValidationError()


class MultiTypeValidator(Validator):
    recognized_keys = {'type', 'minimum', 'maximum'}
    @classmethod
    def _matches(cls, schema):
        return isinstance(schema.get('type', None), list)

    def validate(self, obj):
        raise NotImplementedError()


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

    def validate(self, obj):
        self.make_child(self.children[0]).validate(obj)


class AnyOfValidator(Validator):
    recognized_keys = {'anyOf'}
    @classmethod
    def _matches(cls, schema):
        return 'anyOf' in schema

    @property
    def children(self):
        return self.schema['anyOf']

    def validate(self, obj):
        for child in self.children:
            try:
                self.make_child(child).validate(obj)
            except:
                pass
            else:
                return


class OneOfValidator(Validator):
    recognized_keys = {'oneOf'}
    @classmethod
    def _matches(cls, schema):
        return 'oneOf' in schema

    @property
    def children(self):
        return self.schema['oneOf']

    def validate(self, obj):
        count = 0
        for child in self.children:
            try:
                self.make_child(child).validate(obj)
            except:
                pass
            else:
                count += 1
        if count != 1:
            raise SchemaValidationError()


class AllOfValidator(Validator):
    recognized_keys = {'allOf'}
    @classmethod
    def _matches(cls, schema):
        return 'allOf' in schema

    @property
    def children(self):
        return self.schema['allOf']

    def validate(self, obj):
        for child in self.children:
            self.make_child(child).validate(obj)


class NotValidator(Validator):
    recognized_keys = {'not'}
    @classmethod
    def _matches(cls, schema):
        return 'not' in schema

    @property
    def children(self):
        return [self.schema['not']]

    def validate(self, obj):
        try:
            self.make_child(self.children[0]).validate(obj)
        except SchemaValidationError:
            pass
        else:
            raise SchemaValidationError()
