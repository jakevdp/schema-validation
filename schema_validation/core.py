from .utils import hash_schema


class Schema(object):
    def __init__(self, schema):
        if not isinstance(schema, dict):
            raise ValueError("schema must be a dict")
        self.schema = schema

        # _defined_schemas is a dictionary of all schemas that have been seen.
        self._defined_schemas = {}
        self.tree = self._initialize_child(self.schema)
        self._crawl_children()

    def _initialize_child(self, schema):
        """Initialize a child schema.

        This also updates the _defined_schemas registry, and if the schema
        already appears in this registry then it instead returns a reference
        to the already created object.
        """
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

    def _crawl_children(self):
        seen = set()
        def crawl(obj):
            for child in obj.children:
                hsh = hash_schema(child.schema)
                child.parents.add(obj)
                if hsh not in seen:
                    seen.add(hsh)
                    crawl(child)
        crawl(self.tree)


class _BaseSchema(object):
    def __init__(self, schema, root):
        self.schema = schema
        self.root = root
        self.parents = set()

    @classmethod
    def _validate(cls, schema):
        return False

    def schema_hash(self):
        return hash_schema(self.schema)

    @property
    def children(self):
        return []

    def __repr__(self):
        if len(self.schema) > 3:
            args = ', '.join(sorted(self.schema.keys())[:3]) + '...'
        else:
            args = ', '.join(sorted(self.schema.keys()))
        return "{0}({1})".format(self.__class__.__name__, args)


class ObjectSchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return (schema.get('type', None) == 'object'
                or 'properties' in schema
                or 'additionalProperties' in schema)

    @property
    def children(self):
        props = list(self.schema.get('properties', {}).values())
        addprops = self.schema.get('additionalProperties', None)
        if isinstance(addprops, dict):
            props.append(addprops)
        return [self.root._initialize_child(propschema)
                for propschema in props]


class ArraySchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return 'items' in schema

    @property
    def children(self):
        if 'items' in self.schema:
            return [self.root._initialize_child(self.schema['items'])]
        else:
            return []


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

    @property
    def children(self):
        return [self.root._initialize_child(schema)
                for schema in self.schema['anyOf']]


class RefSchema(_BaseSchema):
    def __init__(self, schema, root):
        super(RefSchema, self).__init__(schema, root)
        self.name = self.schema['$ref']
        self.ref = self.root._initialize_child(self.refschema)

    @classmethod
    def _validate(cls, schema):
        return '$ref' in schema

    @property
    def children(self):
        return self.ref.children

    @property
    def refschema(self):
        keys = self.schema['$ref'].split('/')
        if keys[0] != '#':
            raise ValueError("$ref = {0} not recognized".format(self.schema['$ref']))
        refschema = self.root.schema
        for key in keys[1:]:
            refschema = refschema[key]
        return refschema

    def __repr__(self):
        return "RefSchema('{0}')".format(self.name)


class EmptySchema(_BaseSchema):
    @classmethod
    def _validate(cls, schema):
        return len(schema) == 0 or schema.keys() == {'description'}
