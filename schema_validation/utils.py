import json
import hashlib


def hash_schema(schema, hashfunc=hash):
    """Compute a unique hash for a JSON schema"""
    s = json.dumps(schema, sort_keys=True)
    return hashlib.sha256(s.encode()).hexdigest()
