"""Wishes. Things his person would like, kept as inspiration for forge runs.
A fix run that meets a wish moves it here. Any forge run may grant one."""
import json
import os
import time
from . import paths

PATH = os.path.join(paths.ROOT, "wishes.jsonl")


def all_wishes():
    out = []
    try:
        with open(PATH) as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except OSError:
        pass
    return out


def _write(rows):
    with open(PATH, "w") as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + "\n")


def add(text, source="you"):
    rows = all_wishes()
    wid = "w%03d" % (len(rows) + 1)
    rows.append({"id": wid, "text": text.strip(), "source": source, "granted": None,
                 "at": time.strftime("%Y-%m-%d")})
    _write(rows)
    return wid


def grant(wid, note):
    """A forge run calls this when it made a wish real."""
    rows = all_wishes()
    for r in rows:
        if r["id"] == wid:
            r["granted"] = {"at": time.strftime("%Y-%m-%d"), "note": note}
    _write(rows)


def remove(wid):
    _write([r for r in all_wishes() if r["id"] != wid])


def open_wishes():
    return [r for r in all_wishes() if not r.get("granted")]


def as_text():
    rows = all_wishes()
    if not rows:
        return "- (none yet)"
    out = []
    for r in rows:
        if r.get("granted"):
            out.append("- %s (granted: %s) %s" % (r["id"], r["granted"]["note"], r["text"]))
        else:
            out.append("- %s: %s" % (r["id"], r["text"]))
    return "\n".join(out)
