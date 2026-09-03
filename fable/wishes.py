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


def make(st, text):
    """Spend one wish to write one. Returns (ok, message)."""
    if st["unspent"].get("wish", 0) <= 0:
        return False, "no wishes to make. Levels and luck give them."
    st["unspent"]["wish"] -= 1
    wid = add(text)
    from . import state as S
    S.remember(st, "wish", "wished: " + text[:60])
    return True, wid


def add(text, source="you"):
    rows = all_wishes()
    wid = "w%03d" % (len(rows) + 1)
    rows.append({"id": wid, "text": text.strip(), "source": source, "granted": None,
                 "at": time.strftime("%Y-%m-%d")})
    _write(rows)
    return wid


def grant(wid, note):
    """A forge run calls this when it made a wish real. The wish stays in the
    list, ticked, and the history gets a line."""
    rows = all_wishes()
    for r in rows:
        if r["id"] == wid and not r.get("granted"):
            r["granted"] = {"at": time.strftime("%Y-%m-%d"), "note": note}
            from . import state as S
            st = S.load()
            S.remember(st, "wish", "granted a wish: %s (%s)" % (r["text"][:50], note[:60]))
            S.save(st)
    _write(rows)


def granted():
    return [r for r in all_wishes() if r.get("granted")]


def remove(wid):
    _write([r for r in all_wishes() if r["id"] != wid])


def open_wishes():
    return [r for r in all_wishes() if not r.get("granted")]


def as_text():
    rows = open_wishes()
    if not rows:
        return "- (none)"
    return "\n".join("- %s: %s" % (r["id"], r["text"]) for r in rows)
