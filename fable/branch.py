"""Saves are git branches. `main` is the development branch and holds only the
code. `fable <name>` checks out the save branch <name>, creating it from main if
it is new, and everything the forge makes is committed there."""
import subprocess
from . import paths

PROTECTED = ("main", "master")
PREFIX = "saves/"


def ref(name):
    """The branch for a save name. `trial1` lives at `saves/trial1`."""
    return name if name.startswith(PREFIX) else PREFIX + name


def save_name(branch):
    return branch[len(PREFIX):] if branch.startswith(PREFIX) else branch


def saves():
    rc, out, err = git("branch", "--format=%(refname:short)", "--list", PREFIX + "*")
    return [save_name(b) for b in out.splitlines() if b]


def git(*args):
    p = subprocess.run(["git", *args], cwd=paths.ROOT, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def current():
    return git("rev-parse", "--abbrev-ref", "HEAD")[1]


def exists(name):
    return git("rev-parse", "--verify", "-q", "refs/heads/" + name)[0] == 0


def on_save_branch():
    return current().startswith(PREFIX)


def switch(name):
    """Check out a save branch. Returns (ok, message)."""
    if name in PROTECTED:
        return False, "%s is the development branch. Give Fable a save name." % name
    name = ref(name)
    from . import forge
    if forge.busy():
        return False, "a forge run is going. Wait for it before switching saves."
    if current() == name:
        return True, "on %s" % save_name(name)
    rc, out, err = git("status", "--porcelain")
    if out and current() in PROTECTED:
        # On main, runtime files are junk from running commands there. Drop
        # them, and refuse if hand-written code is uncommitted.
        tracked = [l for l in out.splitlines() if not l.startswith("??")]
        if tracked:
            return False, "uncommitted changes on %s. Commit them first." % current()
        git("clean", "-fdq", "--", "state.json", "events.jsonl", "spending.jsonl", "queue", "items", "presence.json")
    elif out:
        git("add", "-A")
        git("commit", "-qm", "autosave before switching to %s" % name)
    if exists(name):
        rc, out, err = git("checkout", "-q", name)
    else:
        rc, out, err = git("checkout", "-q", "-b", name, "main")
    if rc != 0:
        return False, err[-200:]
    return True, "save %s" % save_name(name)


def upgrade():
    """Bring the code on main into this save."""
    if not on_save_branch():
        return False, "on %s already" % current()
    rc, out, err = git("merge", "--no-edit", "main")
    if rc != 0:
        git("merge", "--abort")
        return False, "merge from main conflicts: " + err[-200:]
    return True, "merged main into %s" % current()
