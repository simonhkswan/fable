"""The talent graph. One JSON per node in talents/. A node is passive (data) or
a skill (a directory with item.json, forged like an item). Neighbours of a node
are generated when you buy it, so the graph grows toward where you spend.

talents/<id>.json
{
  "id": "deep_pockets", "name": "Deep Pockets", "hint": "One more slot.",
  "kind": "passive", "cost": 1, "parent": "root", "pos": [2, -1],
  "effect": {"slots": 1},                 # or {"stat": {"focus": 1}}, {"budget": {"travel": 5}},
                                          # {"discount": {"travel": 1}}, {"weight": {"cosmetic": 2}}
  "generated": false                      # neighbours not yet generated
}
"""
import json
import os
import time
from . import paths, state as S
from .rng import rng_for
from .log import log


def load_all():
    nodes = {}
    for name in sorted(os.listdir(paths.TALENTS)) if os.path.isdir(paths.TALENTS) else []:
        if name.endswith(".json"):
            try:
                with open(os.path.join(paths.TALENTS, name)) as f:
                    n = json.load(f)
                nodes[n["id"]] = n
            except (ValueError, KeyError) as e:
                log("bad talent %s: %s" % (name, e))
    return nodes


def save(node):
    with open(os.path.join(paths.TALENTS, node["id"] + ".json"), "w") as f:
        json.dump(node, f, indent=2, sort_keys=True)
        f.write("\n")


def buyable(nodes, owned):
    out = []
    for n in nodes.values():
        if n["id"] in owned:
            continue
        if n.get("parent") in owned or any(p in owned for p in n.get("parents", [])):
            out.append(n["id"])
    return out


def apply_effect(st, effect):
    for s, n in effect.get("stat", {}).items():
        st["stats"][s] = st["stats"].get(s, 1) + n
    st["slots"] = st.get("slots", 3) + effect.get("slots", 0)


def bonuses(nodes, owned):
    """Sum of passive effects that shape the spec generator."""
    out = {"budget": {}, "discount": {}, "weight": {}}
    for nid in owned:
        n = nodes.get(nid)
        if not n:
            continue
        for key in out:
            for k, v in n.get("effect", {}).get(key, {}).items():
                out[key][k] = out[key].get(k, 0) + v
    return out


def buy(st, nid):
    """Spend a talent point. Returns (ok, message, maybe_job)."""
    nodes = load_all()
    n = nodes.get(nid)
    if not n:
        return False, "no such node", None
    if nid in st["owned_talents"]:
        return False, "already owned", None
    if nid not in buyable(nodes, st["owned_talents"]):
        return False, "not adjacent to anything you own", None
    cost = n.get("cost", 1)
    if st["unspent"]["talent"] < cost:
        return False, "need %d talent point%s" % (cost, "" if cost == 1 else "s"), None
    st["unspent"]["talent"] -= cost
    st["owned_talents"].append(nid)
    apply_effect(st, n.get("effect", {}))
    S.append_jsonl(paths.SPENDING, {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "talent": nid, "cost": cost})
    S.remember(st, "talent", "learned %s" % n.get("name", nid))
    job = None
    if not n.get("generated"):
        from . import sync, rules
        path = st["owned_talents"]
        seed = "talent:" + nid + ":" + "/".join(path[-4:])
        spec = rules.make_spec(seed, "talent", None, st, "level_up")
        spec["node"] = n
        spec["neighbours_wanted"] = rng_for(seed, "n").randint(2, 3)
        spec["existing_nodes"] = [{"id": m["id"], "name": m.get("name"), "kind": m.get("kind"), "pos": m.get("pos")}
                                  for m in nodes.values()]
        job = sync.queue_job("talents", spec, note="branches from %s" % n.get("name", nid))
        n["generated"] = True
        save(n)
    return True, "learned %s" % n.get("name", nid), job


def spend_stat(st, stat):
    if st["unspent"]["stat"] <= 0:
        return False
    st["unspent"]["stat"] -= 1
    st["stats"][stat] = st["stats"].get(stat, 1) + 1
    S.append_jsonl(paths.SPENDING, {"t": time.strftime("%Y-%m-%dT%H:%M:%S"), "stat": stat})
    return True
