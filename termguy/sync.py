"""Turn GitHub events into growth. Loot is not forged here, only queued. You
open it from the widget, one at a time, so you decide when to spend an LLM run."""
import json
import os
import time
from . import paths, state as S, rules, github
from .rng import rng_for
from .log import log


def queue_job(kind, spec, note=""):
    paths.ensure()
    from .rng import seed_of
    short = "%08x" % (seed_of(str(spec.get("seed"))) & 0xffffffff)
    spec.setdefault("id", short)
    job = {
        "id": "%s-%s" % (kind, short),
        "kind": kind, "spec": spec, "note": note,
        "queued": time.strftime("%Y-%m-%dT%H:%M:%S"), "status": "queued",
    }
    path = os.path.join(paths.QUEUE, job["id"] + ".json")
    if os.path.exists(path):
        return None
    with open(path, "w") as f:
        json.dump(job, f, indent=2, sort_keys=True)
    return job


def pending_jobs():
    out = []
    for name in sorted(os.listdir(paths.QUEUE)) if os.path.isdir(paths.QUEUE) else []:
        if name.endswith(".json"):
            with open(os.path.join(paths.QUEUE, name)) as f:
                try:
                    out.append(json.load(f))
                except ValueError:
                    pass
    out = [j for j in out if j.get("status") == "queued"]
    out.sort(key=lambda j: (j.get("queued", ""), j["id"]))
    return out


def apply_event(st, ev):
    """One event, applied. Returns a list of things that happened."""
    seed = ev["seed"]
    happened = []
    is_new_repo = ev["repo"] not in st["repos"]
    if is_new_repo:
        st["repos"].append(ev["repo"])
        happened.append("first %s in %s" % ("merge" if ev["kind"] == "pr" else "review", ev["repo"]))
    xp = rules.xp_of(ev, is_new_repo)
    gains = rules.stat_gains(seed, rules.rules()["stats"])
    for s, n in gains.items():
        st["stats"][s] = st["stats"].get(s, 1) + n
    before = st["level"]
    st["xp"] += xp
    st["level"] = rules.level_for_xp(st["xp"])
    st["counters"][ev["kind"]] = st["counters"].get(ev["kind"], 0) + 1
    rec = {"id": ev["id"], "kind": ev["kind"], "repo": ev["repo"], "number": ev["number"],
           "title": ev["title"], "at": ev.get("at"), "seed": seed, "xp": xp, "gains": gains,
           "categories": len(rules.category_names()), "consumed": time.strftime("%Y-%m-%dT%H:%M:%S")}
    label = "%s %s#%s" % ("merged" if ev["kind"] == "pr" else "reviewed", ev["repo"].split("/")[-1], ev["number"])
    S.remember(st, ev["kind"], "%s  +%d xp  %s" % (label, xp, " ".join("+%d %s" % (n, s) for s, n in gains.items())),
               url=ev.get("url"))
    if rules.roll_drop(seed, ev["kind"]):
        spec = rules.make_spec(seed, "drop", ev, st, "drop")
        job = queue_job("item", spec, note="dropped by " + label)
        if job:
            st["counters"]["drops"] = st["counters"].get("drops", 0) + 1
            rec["drop"] = spec["rarity"]
            happened.append("a %s drop from %s" % (spec["rarity"], label))
            S.remember(st, "drop", "something %s fell out of %s" % (spec["rarity"], label))
    pts = rules.rules()["points_per_level"]
    for lvl in range(before + 1, st["level"] + 1):
        st["unspent"]["stat"] += pts["stat"]
        st["unspent"]["talent"] += pts["talent"]
        st["counters"]["level_ups"] = st["counters"].get("level_ups", 0) + 1
        happened.append("level %d" % lvl)
        S.remember(st, "level", "reached level %d" % lvl)
        every = rules.rules()["level_up_item_every"]
        if every and lvl % every == 0:
            lseed = "level:%d:" % lvl + seed
            spec = rules.make_spec(lseed, "level", ev, st, "level_up")
            spec["level_reached"] = lvl
            queue_job("item", spec, note="reward for level %d" % lvl)
            rec.setdefault("level_items", []).append(spec["rarity"])
        m = rules.rules()["talent_milestone_every"]
        if m and lvl % m == 0:
            cseed = "milestone:%d:" % lvl + seed
            spec = rules.make_spec(cseed, "milestone", ev, st, "level_up")
            spec["category"] = "__new__"
            spec["level_reached"] = lvl
            queue_job("category", spec, note="milestone at level %d" % lvl)
    st["seen_events"].append(ev["id"])
    S.append_jsonl(paths.EVENTS, rec)
    return happened


def run(since=None, progress=None, dry=False):
    st = S.load()
    seen = set(st["seen_events"])
    fresh = github.fetch_new(seen, since=since, progress=progress)
    all_happened = []
    for ev in fresh:
        if dry:
            all_happened.append(ev["id"])
            continue
        all_happened += apply_event(st, ev)
    if not dry:
        st["last_sync"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        S.save(st)
    log("sync: %d new events, %d notes" % (len(fresh), len(all_happened)))
    return fresh, all_happened
