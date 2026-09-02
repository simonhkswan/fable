"""What generated code gets handed. A convenience, not a fence: items can also
call subprocess or anything else directly."""
import json
import os
import subprocess
from . import paths, state as S
from .log import log


class World:
    def __init__(self, st=None):
        self.dir = paths.ROOT
        self.pane_id = os.environ.get("ZELLIJ_PANE_ID")
        self.session = os.environ.get("ZELLIJ_SESSION_NAME")
        self._st = st

    # ── state ──
    @property
    def state(self):
        return self._st if self._st is not None else S.load()

    def save(self):
        if self._st is not None:
            S.save(self._st)

    def remember(self, text, kind="item"):
        S.remember(self.state, kind, text)

    # ── zellij ──
    def zellij(self, *args, timeout=10):
        if not self.session:
            return ""
        p = subprocess.run(["zellij", "action", *map(str, args)], capture_output=True,
                           text=True, timeout=timeout)
        if p.returncode != 0:
            log("zellij %s: %s" % (" ".join(map(str, args)), p.stderr.strip()[:200]))
        return p.stdout.strip()

    def list_panes(self):
        out = []
        for line in self.zellij("list-panes").splitlines()[1:]:
            parts = line.split(None, 2)
            if len(parts) >= 2:
                out.append({"id": parts[0], "type": parts[1], "title": parts[2] if len(parts) > 2 else ""})
        return out

    def open_portal(self, command, x="10%", y="10%", width="30%", height="30%", name=None,
                    focus=False, borderless=False, pinned=True):
        """A floating pane running `command` (list). Returns the pane id."""
        args = ["new-pane", "-f", "-c", "-x", x, "-y", y, "--width", width, "--height", height,
                "--pinned", "true" if pinned else "false"]
        if name:
            args += ["-n", name]
        if not focus:
            args.append("--no-focus")
        if borderless:
            args += ["--borderless", "true"]
        args += ["--", *command]
        pid = self.zellij(*args)
        if pid:
            st = self.state
            st.setdefault("owned_panes", []).append(pid)
            self.save()
        return pid

    def glide(self, pane_id, x=None, y=None, width=None, height=None):
        args = ["change-floating-pane-coordinates", "-p", pane_id]
        for k, v in (("-x", x), ("-y", y), ("--width", width), ("--height", height)):
            if v is not None:
                args += [k, str(v)]
        self.zellij(*args)

    def possess(self, pane_id, command):
        """Run `command` in place of another pane. The pane comes back when it exits."""
        return self.zellij("new-pane", "-i", "--close-replaced-pane=false", "--pane-id", pane_id,
                           "-c", "--", *command)

    def close_owned(self):
        st = self.state
        for pid in list(st.get("owned_panes", [])):
            subprocess.run(["zellij", "action", "focus-pane-id", pid], capture_output=True)
            subprocess.run(["zellij", "action", "close-pane"], capture_output=True)
            st["owned_panes"].remove(pid)
        self.save()

    def dump_screen(self, pane_id=None):
        p = subprocess.run(["zellij", "action", "dump-screen", "/dev/stdout"] if pane_id is None else
                           ["zellij", "action", "dump-screen", "/dev/stdout"], capture_output=True, text=True)
        return p.stdout

    # ── the outside ──
    def sh(self, cmd, timeout=30):
        p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return p.stdout

    def claude(self, prompt, timeout=120):
        p = subprocess.run(["claude", "-p", prompt], capture_output=True, text=True, timeout=timeout)
        return p.stdout.strip()

    def say(self, text, seconds=4.0):
        """A speech bubble in the home pane, through the presence file."""
        try:
            with open(paths.PRESENCE) as f:
                pres = json.load(f)
        except (OSError, ValueError):
            pres = {}
        pres["say"] = {"text": text, "until": __import__("time").time() + seconds}
        with open(paths.PRESENCE, "w") as f:
            json.dump(pres, f)
