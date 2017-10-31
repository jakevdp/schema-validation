"""
JSONSchema class implementation
"""

from .utils import hash_schema, nested_dict_repr
from .validators import Validator


class JSONSchema(object):
    """Wrapper for a JSON schema

    Parameters
    ----------
    schema : dict
        a jsonschema dictionary

    Attributes
    ----------
    schema : dict
        the schema dictionary
    root : JSONSchema object
        a pointer to the root schema
    validators : list
        a list of Validator classes for this level of the schema
    parents : list
        a list of parent objects to the current schema

    Notes
    -----
    The root JSONSchema has a _registry attribute, which is a dictionary mapping
    unique hashes of each schema to a JSONSchema object which wraps it. When the
    tree of schema objects is created, this registry is used to identify
    when two schemas are identical, both for efficiency and to detect
    cyclical schema definitions.

    Because of this, the ``parents`` attribute is able to point to all parents
    of each unique schema, even if it occurs multiple times in the schema tree.

    Each schema will match zero or more "validator" classes, which can be used
    to validate input.
    """
    def __init__(self, schema, warn_on_unused=True, **kwds):
        unrecognized_args = kwds.keys() - {'root'}
        if unrecognized_args:
            raise ValueError('Unrecognized arguments to JSONSchema: {0}'
                             ''.format(unrecognized_args))
        self.schema = schema
        self.root = kwds.get('root', self)
        self.validators = Validator._initialize_validators(self)
        self.parents = []

        # Because of the use of the registry, we need to finish object creation
        # before instantiating children. For that reason, we recursively
        # create children from the root instance.
        if self is self.root:
            hsh = self._schema_hash()
            self._registry = {hsh: self}
            self._schema_to_name = {hsh: '#'}
            self._definitions = {'#': self.schema}
            self._recursively_create_children()

    def _schema_hash(self):
        return hash_schema(self.schema)

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
        """Registry of instantiated JSONSchema objects"""
        return self.root._registry

    @property
    def name(self):
        """Return the object name if any"""
        return self.root._schema_to_name.get(self._schema_hash(), None)

    def _recursively_create_children(self):
        seen = set()
        def crawl(obj):
            for child in obj.children:
                hsh = child._schema_hash()
                if hsh not in seen:
                    seen.add(hsh)
                    crawl(child)
        crawl(self)

    def initialize_child(self, schema):
        """Return a JSONSchema object wrapping a child schema"""
        key = hash_schema(schema)
        if key not in self.registry:
            self.registry[key] = JSONSchema(schema, root=self.root)
        obj = self.registry[key]
        if self not in obj.parents:
            obj.parents.append(self)
        return obj

    def resolve_ref(self, ref):
        """Resolve a reference within a schema"""
        if ref not in self.root._definitions:
            keys = ref.split('/')
            if keys[0] != '#':
                raise ValueError("$ref = {0} not recognized: must start with #"
                                 "".format(self.schema['$ref']))
            refschema = self.root.schema
            for key in keys[1:]:
                refschema = refschema[key]
            self.root._definitions[ref] = refschema
            self.root._schema_to_name[hash_schema(refschema)] = ref
        return self.root._definitions[ref]

    @property
    def children(self):
        return [self.initialize_child(schema)
                for schema in self.iter_child_schemas()]

    def iter_child_schemas(self):
        for key in ['properties', 'patternProperties']:
            for child in self.schema.get(key, {}).values():
                yield child
        for key in ['anyOf', 'oneOf', 'allOf']:
            for child in self.schema.get(key, []):
                yield child
        for key in ['additionalProperties', 'not', 'items']:
            val = self.schema.get(key, None)
            if isinstance(val, dict):
                yield val
        if '$ref' in self.schema:
            yield self.resolve_ref(self.schema['$ref'])

    def __repr__(self):
        return "JSONSchema({0})".format(self.validators)

    def validate(self, obj):
        for validator in self.validators:
            validator.validate(obj)
