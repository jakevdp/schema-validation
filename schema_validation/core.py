from .utils import hash_schema


class Schema(object):
    def __init__(self, schema):
        self.schema = schema
        self._defined_schemas = {}
        self.tree = self.initialize_child(self.schema)

    def initialize_child(self, schema):
        key = hash_schema(schema)

        if key in self._defined_schemas:
            obj = self._defined_schemas[key]
        else:
            valid_classes = [cls for cls in _BaseSchema.__subclasses__()
                             if cls._validate(schema)]
            if len(valid_classes) == 0:
                raise ValueError("No valid class for schema {0}"
                                 "".format(schema))
            elif len(valid_classes) > 1:
                raise ValueError("Schema matches multiple classes: {0}\n{1}"
                                 "".format(valid_classes, schema))

            obj = valid_classes[0](schema, root=self)
            self._defined_schemas[key] = obj
        return obj


class _BaseSchema(object):
    def __init__(self, schema, root):
        self.schema = schema
        self.root = root

    @classmethod
    def _validate(cls, schema):
        return False

    def schema_hash(self):
        return hash_schema(self.schema)

    def children(self):
        return []


class ObjectSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return 'properties' in schema

    def children(self):
        return [self.root.initialize_child(propschema)
                for prop, propschema in self.schema['properties'].items()]


class ArraySchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return 'items' in schema


class NumberTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == 'number'


class IntegerTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == 'integer'


class StringTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == 'string'


class NullTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == 'null'


class BooleanTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == 'boolean'


class MultiTypeSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return isinstance(schema.get('type', None), list)


class AnyOfSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return 'anyOf' in schema

    def children(self):
        return [self.root.initialize_child(schema)
                for schema in self.schema['anyOf']]


class RefSchema(_BaseSchema):
    def __init__(self, schema, root):
        super(RefSchema, self).__init__(schema, root)
        self.name = self._refname()
        self.ref = self._refobj()

    @classmethod
    def _validate(cls, schema):
        return '$ref' in schema

    def children(self):
        return self.ref.children()

    def _refname(self):
        return self.schema['$ref'].split('/')[-1]

    def _refobj(self):
        keys = self.schema['$ref'].split('/')
        if keys[0] != '#':
            raise ValueError("$ref = {0} not recognized".format(self.schema['$ref']))
        refschema = self.root.schema
        for key in keys[1:]:
            refschema = refschema[key]
        return self.root.initialize_child(refschema)
