"""A forge run is a Claude Code session in this directory with a brief built
from a template and the seeded variables of one job. Nothing is off limits to
it. After the run, the boot test runs. If it fails, a repair session gets the
error. If that fails too, the run is reverted."""
import fcntl
import json
import os
import shutil
import subprocess
import time
from . import paths, state as S, rules, talents, tables, wishes
from .log import log

CLAUDE = ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "text"]


def git(*args):
    return subprocess.run(["git", *args], cwd=paths.ROOT, capture_output=True, text=True).stdout


def read(path):
    with open(path) as f:
        return f.read()


def fill(template, vars_):
    out = template
    for k, v in vars_.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def facts(st):
    """The live half of the brief."""
    from . import items as I
    cats = []
    for name in rules.category_names():
        with open(os.path.join(paths.CATEGORIES, name, "manifest.json")) as f:
            m = json.load(f)
        cats.append("- %s (weight %s): %s" % (name, m.get("weight", 1), m.get("tagline", "")))
    its = []
    for it in I.scan():
        its.append("- %s [%s %s] %s" % (it.name, it.rarity, it.category, it.m.get("flavor", "")[:80]))
    nodes = talents.load_all()
    owned = st["owned_talents"]
    tal = ["- %s%s (%s)" % (n.get("name", n["id"]), " *" if n["id"] in owned else "", n.get("kind", "passive"))
           for n in nodes.values()]
    return {
        "state_json": json.dumps({k: st[k] for k in ("name", "level", "xp", "stats", "unspent", "slots", "equipped", "counters")}, indent=1),
        "categories": "\n".join(cats) or "- (none)",
        "items": "\n".join(its) or "- (none yet)",
        "talents": "\n".join(tal) or "- (none)",
        "git_log": git("log", "--oneline", "-15") or "(no commits yet)",
        "history": "\n".join("- " + h["text"] for h in st.get("history", [])[-12:]),
        "wishes": wishes.as_text(),
        "tree": subprocess.run(["find", ".", "-maxdepth", "2", "-not", "-path", "./.git*", "-not", "-path", "./runs*",
                                "-not", "-name", "*.pyc", "-not", "-path", "*/__pycache__*"],
                               cwd=paths.ROOT, capture_output=True, text=True).stdout,
    }


def brief_for(job):
    spec = job["spec"]
    st = S.load()
    kind = job["kind"]
    name = {"item": "forge_brief.md", "category": "category_brief.md", "talents": "talent_brief.md",
            "fix": "fix_brief.md"}[kind]
    if spec.get("category") == "__new__" and kind == "item":
        name = "category_brief.md"
    template = read(os.path.join(paths.TEMPLATES, name))
    bon = talents.bonuses(talents.load_all(), st["owned_talents"])
    rar = tables.load("rarity")
    scope_t = tables.load("scope")
    odds = rar["level_up" if spec.get("source") in ("level", "milestone", "talent") else "drop"]
    total = sum(odds.values()) or 1
    order = ["common", "rare", "epic", "legendary", "ultra"] + [k for k in rar["budget"] if k not in ("common", "rare", "epic", "legendary", "ultra")]
    rarities = ", ".join("%s %.1f%%" % (k, 100.0 * odds[k] / total) for k in order if k in odds)
    scopes = "; ".join("%s: %s" % (k, v_) for k, v_ in scope_t["brief"].items())
    lo = min(b[0] for b in rar["budget"].values())
    hi = max(b[1] for b in rar["budget"].values())
    this_lo, this_hi = rar["budget"].get(spec.get("rarity"), [lo, hi])
    v = dict(facts(st))
    v.update({
        "job_id": job["id"], "note": job.get("note", ""), "kind": kind,
        "spec_json": json.dumps(spec, indent=1),
        "rarity": spec.get("rarity"), "scope": spec.get("scope"), "scope_brief": spec.get("scope_brief"),
        "budget": spec.get("budget", 0) + bon["budget"].get(spec.get("category"), 0),
        "category": spec.get("category"), "mood": spec.get("mood"), "constraint": spec.get("constraint"),
        "twist": spec.get("twist") or "none", "theme": ", ".join(spec.get("theme", [])) or "none",
        "requires": json.dumps(spec.get("requires")), "seed": spec.get("seed"),
        "event": json.dumps(spec.get("event")), "item_id": spec.get("id") or str(spec.get("seed", "x"))[:8],
        "contract": read(os.path.join(paths.TEMPLATES, "contract.md")),
        "rarities": rarities, "scopes": scopes,
        "budget_range": "%d to %d overall; %d to %d for a %s" % (lo, hi, this_lo, this_hi, spec.get("rarity")),
        "category_list": ", ".join(rules.category_names()) + ", or a new one",
        "report": spec.get("report", ""), "page": spec.get("page", "home"), "when": job.get("queued", ""),
        "save": subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=paths.ROOT, capture_output=True, text=True).stdout.strip(),
        "errors": "\n".join("- " + e for e in spec.get("errors", [])) or "- (none)",
    })
    return fill(template, v)


def boot_test():
    p = subprocess.run([os.path.join(paths.ROOT, "bin", "fable"), "boot-test"], cwd=paths.ROOT,
                       capture_output=True, text=True, timeout=180)
    return p.returncode == 0, (p.stdout + p.stderr)[-4000:]


def run_claude(prompt, run_dir, tag):
    with open(os.path.join(run_dir, tag + "-brief.md"), "w") as f:
        f.write(prompt)
    # A forge run must not look like a child of the session that started it.
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    with open(os.path.join(run_dir, tag + "-out.txt"), "w") as out:
        p = subprocess.run(CLAUDE, input=prompt, cwd=paths.ROOT, stdout=out, stderr=subprocess.STDOUT,
                           text=True, timeout=60 * 40, env=env)
    return p.returncode


def snapshot(tag):
    """A commit of everything, so a run can be undone."""
    git("add", "-A")
    git("commit", "-qm", tag, "--allow-empty")
    return git("rev-parse", "HEAD").strip()


def undo_to(commit):
    """Put the working tree back to a commit. Only files the forge touched."""
    git("checkout", "-q", commit, "--", ".")
    git("clean", "-fdq", "--", "items", "categories", "talents", "fable", "tables", "templates")
    git("commit", "-qm", "undo failed forge", "--allow-empty")


LOCK = os.path.join(paths.ROOT, ".forge.lock")


def busy():
    """True while any process holds the forge lock."""
    try:
        f = open(LOCK, "w")
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    fcntl.flock(f, fcntl.LOCK_UN)
    f.close()
    return False


def run_job(job, on_status=None):
    """Run one queued job to completion. Returns (ok, message). One forge run
    at a time, machine wide: two runs in one git repo would tangle."""
    paths.ensure()
    say = on_status or (lambda s: None)
    from . import branch
    if not branch.on_save_branch():
        return False, "on %s, the development branch. Run `fable <save-name>` first." % branch.current()
    lock = open(LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False, "another forge run is going. Wait for it."
    try:
        return _run_job(job, say)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


CURRENT = os.path.join(paths.RUNS, "current.json")


def write_current(job, status):
    try:
        with open(CURRENT, "w") as f:
            json.dump({"job": job["id"], "note": job.get("note", ""), "status": status,
                       "started": job.get("_started", time.time()), "pid": os.getpid()}, f)
    except OSError:
        pass


def current():
    """What the forge is doing right now, or None."""
    if not busy():
        return None
    try:
        with open(CURRENT) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {"job": "?", "status": "forging", "started": time.time()}


def spawn(job_id):
    """Start a forge run as its own process, so the widget can come and go."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("CLAUDE")}
    subprocess.Popen([os.path.join(paths.ROOT, "bin", "fable"), "forge", job_id], cwd=paths.ROOT, env=env,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def _run_job(job, say0):
    job["_started"] = time.time()

    def say(status):
        write_current(job, status)
        say0(status)
    run_dir = os.path.join(paths.RUNS, time.strftime("%Y%m%d-%H%M%S") + "-" + job["id"])
    os.makedirs(run_dir, exist_ok=True)
    shutil.copy(paths.STATE, os.path.join(run_dir, "state-before.json"))
    base = snapshot("before forge %s" % job["id"])
    mark_job(job, "running")
    say("forging %s (%s %s)" % (job["id"], job["spec"].get("rarity"), job["spec"].get("scope")))
    brief = brief_for(job)
    rc = run_claude(brief, run_dir, "forge")
    log("forge %s: claude exit %d" % (job["id"], rc))
    ok, out = boot_test()
    tries = 0
    while not ok and tries < 2:
        tries += 1
        say("boot test failed, repairing (%d)" % tries)
        repair = read(os.path.join(paths.TEMPLATES, "repair_brief.md"))
        repair = repair.replace("{{error}}", out).replace("{{job_id}}", job["id"])
        run_claude(repair, run_dir, "repair%d" % tries)
        ok, out = boot_test()
    if not ok:
        log("forge %s: undoing, boot test still failing:\n%s" % (job["id"], out))
        undo_to(base)
        shutil.copy(os.path.join(run_dir, "state-before.json"), paths.STATE)
        job.pop("_started", None)
        mark_job(job, "failed", out[-800:])
        return False, "the forge failed and was undone. See %s" % run_dir
    snapshot("forge %s: %s" % (job["id"], job.get("note", "")))
    job.pop("_started", None)
    mark_job(job, "done")
    st = S.load()
    S.remember(st, "forge", "forged %s" % job.get("note", job["id"]))
    S.save(st)
    return True, "forged. See git log."


def mark_job(job, status, error=None):
    job["status"] = status
    job["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    if error:
        job["error"] = error
    path = os.path.join(paths.QUEUE, job["id"] + ".json")
    if status in ("done", "failed"):
        done_dir = os.path.join(paths.QUEUE, "done")
        os.makedirs(done_dir, exist_ok=True)
        with open(os.path.join(done_dir, job["id"] + ".json"), "w") as f:
            json.dump(job, f, indent=2, sort_keys=True)
        if os.path.exists(path):
            os.remove(path)
    else:
        with open(path, "w") as f:
            json.dump(job, f, indent=2, sort_keys=True)
