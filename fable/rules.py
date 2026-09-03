"""Growth arithmetic and seeded rolls. Everything reads from tables/."""
import math
import os
from . import tables, paths, rng as R


def rules():
    return tables.load("rules")


def xp_for_level(n):
    """Total xp at which level n begins. Level 1 begins at zero."""
    if n <= 1:
        return 0
    c = rules()["level_curve"]
    return int(c["base"] * (n ** c["power"]))


def level_for_xp(xp):
    n = 1
    while xp >= xp_for_level(n + 1) and n < 999:
        n += 1
    return n


def xp_of(event, is_new_repo):
    x = rules()["xp"]
    if event["kind"] == "pr":
        lines = event.get("additions", 0) + event.get("deletions", 0)
        xp = x["pr_base"]
        xp += min(x["pr_lines_cap"], (lines // 10) * x["pr_per_10_lines"])
        xp += min(x["pr_files_cap"], event.get("files", 0) * x["pr_per_file"])
    else:
        xp = x["review_base"]
        xp += min(x["review_comments_cap"],
                  event.get("comments", 0) * x["review_per_comment"])
    if is_new_repo:
        xp += x["new_repo_bonus"]
    return int(xp)


def stat_gains(seed, kind):
    """Reviews feed one stat. PRs feed a small pool. Most events feed nothing,
    so the stats you choose to spend points on stay the ones that define him."""
    g = rules()["stat_gain"].get(kind) or {"chance": 0, "stats": []}
    rng = R.rng_for(seed, "stats")
    if not g["stats"] or rng.random() >= g["chance"]:
        return {}
    return {rng.choice(g["stats"]): 1}


def category_names():
    out = []
    for name in sorted(os.listdir(paths.CATEGORIES)):
        if os.path.exists(os.path.join(paths.CATEGORIES, name, "manifest.json")):
            out.append(name)
    return out


def category_weights():
    import json
    weights = {}
    for name in category_names():
        with open(os.path.join(paths.CATEGORIES, name, "manifest.json")) as f:
            m = json.load(f)
        weights[name] = m.get("weight", 1)
    return weights


def new_category_weight(n_categories):
    c = rules()["new_category"]
    return c["base"] * (c["decay"] ** max(0, n_categories - c["grace"]))


def roll_drop(seed, kind):
    rng = R.rng_for(seed, "drop")
    return rng.random() < rules()["drop_chance"][kind]


def theme_words(event):
    words = []
    repo = event.get("repo", "")
    if repo:
        words.append(repo.split("/")[-1])
    title = event.get("title", "")
    for w in title.replace("(", " ").replace(")", " ").replace(":", " ").split():
        w = w.strip(".,[]:;!?\"'").lower()
        if len(w) > 3 and not w.startswith("eng-") and not w.startswith("tec-"):
            words.append(w)
    exts = {}
    for p in event.get("paths", []):
        e = os.path.splitext(p)[1].lstrip(".")
        if e:
            exts[e] = exts.get(e, 0) + 1
    words += [e for e, _ in sorted(exts.items(), key=lambda kv: -kv[1])[:3]]
    seen = set()
    out = []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out[:8]


def make_spec(seed, source, event, st, rarity_table):
    """The structured half of a reward. The LLM sees this and may ignore it."""
    rar = tables.load("rarity")
    scope_t = tables.load("scope")
    rng = R.rng_for(seed, "spec")
    rarity = R.weighted(rng, rar[rarity_table])
    scope = R.weighted(rng, scope_t["by_rarity"][rarity])
    lo, hi = rar["budget"][rarity]
    budget = rng.randint(lo, hi)
    lo, hi = rar["level_offset"][rarity]
    level_req = max(1, st["level"] + rng.randint(lo, hi))
    stats = rules()["stats"]
    n_req = rar["stat_reqs"][rarity]
    stat_req = {}
    for s in rng.sample(stats, n_req):
        stat_req[s] = max(1, st["stats"][s] + rng.randint(0, 2 + level_req // 5))
    weights = category_weights()
    weights["__new__"] = new_category_weight(len(weights))
    category = R.weighted(rng, weights)
    mood = rng.choice(tables.load("mood"))
    constraint = rng.choice(tables.load("constraint"))
    tw = tables.load("twist")
    twist = rng.choice(tw["list"]) if rng.random() < tw["chance"] else None
    return {
        "seed": seed,
        "source": source,
        "rarity": rarity,
        "scope": scope,
        "scope_brief": scope_t["brief"][scope],
        "budget": budget,
        "requires": {"level": level_req, "stats": stat_req},
        "category": category,
        "theme": theme_words(event) if event else [],
        "mood": mood,
        "constraint": constraint,
        "twist": twist,
        "event": {k: event.get(k) for k in ("id", "kind", "repo", "number", "title", "url")} if event else None,
        "fable": {"level": st["level"], "stats": dict(st["stats"])},
        "categories_at_roll": len(weights) - 1,
    }
