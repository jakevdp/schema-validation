from .utils import hash_schema


class Schema(object):
    _defined_objects = {}
    
    def __init__(self, schema, parent=None):
        self.schema = schema
        self.parent = parent
        self.top = parent.top if parent is not None else self
        self._bases = set()
        
    def __hash__(self):
        return hash_schema(self.schema)
    
    @classmethod
    def _validate(cls, schema):
        return False
    
    @classmethod
    def initialize(cls, schema, parent=None, base=None):
        key = hash_schema(schema)
        if key in cls._defined_objects:
            obj = cls._defined_objects[key]
        else:
            valid_classes = [cls for cls in Schema.__subclasses__()
                             if cls._validate(schema)]
            if len(valid_classes) == 0:
                raise ValueError("No valid class for schema {0}"
                                 "".format(schema))
            elif len(valid_classes) > 1:
                raise ValueError("Schema with keys {0} matches multiple classes: {1}"
                                 "".format(schema.keys(), valid_classes))

            obj = valid_classes[0](schema, parent=parent)
            cls._defined_objects[key] = obj
            
        if base is not None:
            obj._bases.add(base)
            
        return obj
    
    def children(self):
        return []

class ObjectSchema(Schema):
    @classmethod
    def _validate(cls, schema):
        return 'properties' in schema
        
    def children(self):
        return [self.initialize(propschema, parent=self)
                for prop, propschema in self.schema['properties'].items()]
    
class ArraySchema(Schema):
    @classmethod
    def _validate(cls, schema):
        return 'items' in schema
    
class NullType(Schema):
    type = 'null'
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == cls.type
            
class SimpleTypeMixin(object):
    @classmethod
    def _validate(cls, schema):
        return schema.get('type', None) == cls.type
    
class NumberTypeSchema(SimpleTypeMixin, Schema):
    type = 'number'
    
class IntegerTypeSchema(SimpleTypeMixin, Schema):
    type = 'integer'
    
class StringTypeSchema(SimpleTypeMixin, Schema):
    type = 'string'
    
class BooleanTypeSchema(SimpleTypeMixin, Schema):
    type = 'boolean'
    
class MultiTypeSchema(Schema):
    @classmethod
    def _validate(cls, schema):
        return isinstance(schema.get('type', None), list)
    
class AnyOfSchema(Schema):
    @classmethod
    def _validate(cls, schema):
        return 'anyOf' in schema
    
    def children(self):
        return [self.initialize(schema, parent=self, base=self)
                for schema in self.schema['anyOf']]
    
class RefSchema(Schema):
    def __init__(self, schema, parent=None):
        super(RefSchema, self).__init__(schema, parent)
        keys = self.schema['$ref'].split('/')
        if keys[0] != '#':
            raise ValueError("$ref = {0} not recognized".format(self.schema['$ref']))
        self.name = keys[-1]
        refschema = self.top.schema
        for key in keys[1:]:
            refschema = refschema[key]
        self._ref = self.initialize(refschema, parent=self)
    
    @classmethod
    def _validate(cls, schema):
        return '$ref' in schema
            
    def children(self):
        return self._ref.children()
