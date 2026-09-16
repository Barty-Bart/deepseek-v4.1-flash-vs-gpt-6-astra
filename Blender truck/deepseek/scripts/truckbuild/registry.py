"""Shared registry so later build stages can find parts created by earlier ones."""
PARTS = {}

def put(key, obj):
    PARTS[key] = obj
    return obj

def get(key, default=None):
    return PARTS.get(key, default)

def require(key):
    if key not in PARTS:
        raise KeyError('registry has no part %r' % key)
    return PARTS[key]

def add_to_group(key, obj):
    PARTS.setdefault(key, []).append(obj)
    return obj
