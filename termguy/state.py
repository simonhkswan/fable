import json
import os
import time
from . import paths, tables


def default_state():
    rules = tables.load("rules")
    return {
        "version": 1,
        "name": "the guy",
        "level": 1,
        "xp": 0,
        "stats": {s: 1 for s in rules["stats"]},
        "unspent": {"stat": 0, "talent": 0},
        "slots": rules["starting_slots"],
        "equipped": [],
        "seen_events": [],
        "repos": [],
        "owned_talents": ["root"],
        "owned_panes": [],
        "counters": {"pr": 0, "review": 0, "drops": 0, "level_ups": 0},
        "history": [],
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def load():
    try:
        with open(paths.STATE) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = default_state()
        save(st)
    return st


def save(st):
    tmp = paths.STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, paths.STATE)


def mtime():
    try:
        return os.path.getmtime(paths.STATE)
    except OSError:
        return 0.0


def append_jsonl(path, rec):
    with open(path, "a") as f:
        f.write(json.dumps(rec, sort_keys=True) + "\n")


def read_jsonl(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def remember(st, kind, text, **extra):
    """A line in the guy's history, shown on the log page."""
    rec = {"t": time.strftime("%Y-%m-%d %H:%M"), "kind": kind, "text": text}
    rec.update(extra)
    st.setdefault("history", []).append(rec)
    del st["history"][:-400]
