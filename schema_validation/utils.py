import json
import hashlib


def nested_dict_repr(obj, depth=1):
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


def copy_and_drop(D, keys):
    return {key: val for key, val in D.items()
            if key in keys}


def split_dict(D, keys):
    D_in = {key: val for key, val in D.items()
            if key in keys}
    D_out = {key: val for key, val in D.items()
             if key not in keys}
    return D_in, D_out


def hash_schema(schema, hashfunc=hash):
    """Compute a unique hash for a JSON schema"""
    s = json.dumps(schema, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()
