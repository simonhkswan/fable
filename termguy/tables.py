"""Tables are files, so a forge run can change the odds."""
import json
import os
from . import paths

_cache = {}


def load(name, default=None):
    path = os.path.join(paths.TABLES, name + ".json")
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return default
    hit = _cache.get(name)
    if hit and hit[0] == mtime:
        return hit[1]
    with open(path) as f:
        data = json.load(f)
    _cache[name] = (mtime, data)
    return data


def save(name, data):
    path = os.path.join(paths.TABLES, name + ".json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
