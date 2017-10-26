import json
import hashlib


def nested_dict_repr(obj, depth=1):
    """Return an object with a cleaner representation of a nested dict"""
    class EllipsisDict(object):
        def __repr__(self):
            return "{...}"

    if isinstance(obj, dict):
        if depth <= 0:
            return EllipsisDict()
        else:
            return {k: nested_dict_repr(v, depth - 1)
                    for k, v in obj.items()}
    else:
        return obj


def hash_schema(schema, hashfunc=hashlib.sha256):
    """Compute a unique hash for a JSON schema"""
    s = json.dumps(schema, sort_keys=True)
    return hashfunc(s.encode()).hexdigest()


def isnumeric(val):
    return isinstance(val, (int, float)) and not isinstance(val, bool)
