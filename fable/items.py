"""Items and skills are directories with a manifest. The manifest says how the
widget reaches the code: run it once, keep it running and stream JSON lines, or
import it into the process.

items/<id>/item.json
{
  "id": "a3f9c2", "name": "Cape of Small Hours", "flavor": "...",
  "category": "cosmetic", "rarity": "rare",
  "requires": {"level": 7, "stats": {"focus": 4}},
  "attach": {
    "register": {"import": "cape.py"},          # register(anim, world)
    "key:c": {"run": "./cast.sh"},              # run once on the key
    "tick": {"stream": "node aura.js"},         # long-lived, JSON lines
    "event:pr_merged": {"run": "uv run celebrate.py"}
  },
  "build": "optional shell command run once after forging"
}
"""
import importlib.util
import json
import os
import subprocess
import sys
import threading
from . import paths
from .log import log


class Item:
    def __init__(self, path, manifest):
        self.path = path
        self.m = manifest
        self.id = manifest.get("id") or os.path.basename(path)
        self.procs = {}
        self.stream_out = {}

    @property
    def name(self): return self.m.get("name", self.id)
    @property
    def rarity(self): return self.m.get("rarity", "common")
    @property
    def category(self): return self.m.get("category", "misc")
    @property
    def skill(self): return bool(self.m.get("skill"))

    def missing(self, st):
        """What Fable still lacks to use this. Empty means usable."""
        if self.skill:
            return []
        req = self.m.get("requires", {})
        out = []
        if st["level"] < req.get("level", 0):
            out.append("level %d" % req["level"])
        for s, n in req.get("stats", {}).items():
            if st["stats"].get(s, 0) < n:
                out.append("%s %d" % (s, n))
        return out

    def env(self, world):
        e = dict(os.environ)
        e.update({
            "GUY_DIR": paths.ROOT, "GUY_ITEM_DIR": self.path, "GUY_STATE": paths.STATE,
            "GUY_ITEM_ID": self.id, "GUY_PANE_ID": world.pane_id or "",
        })
        try:
            w, h = os.get_terminal_size(sys.stdout.fileno())
            e["GUY_COLS"], e["GUY_ROWS"] = str(w), str(h)
        except OSError:
            pass
        return e

    # ── attaching ──
    def attach(self, anim, world, guy):
        for point, how in self.m.get("attach", {}).items():
            try:
                self._attach_one(point, how, anim, world, guy)
            except Exception as e:  # noqa: BLE001
                anim.fail("%s %s" % (self.name, point), e)
                log("attach %s %s: %s" % (self.id, point, e))

    def _attach_one(self, point, how, anim, world, guy):
        if "import" in how:
            mod = self._import(how["import"])
            if point == "register" and hasattr(mod, "register"):
                mod.register(anim, world)
            elif point.startswith("key:") and hasattr(mod, "main"):
                anim.key(point[4:], lambda ctx, m=mod: m.main(ctx, world), how.get("help", self.name))
            elif point.startswith("event:") and hasattr(mod, "main"):
                anim.reaction(point[6:], lambda ctx, data, m=mod: m.main(ctx, world, data))
            elif point == "tick" and hasattr(mod, "main"):
                anim.tick(lambda ctx, m=mod: m.main(ctx, world))
            return
        if "run" in how:
            cmd = how["run"]
            if point.startswith("key:"):
                anim.key(point[4:], lambda ctx: self.run(cmd, world), how.get("help", self.name))
            elif point.startswith("event:"):
                anim.reaction(point[6:], lambda ctx, data: self.run(cmd, world, data))
            elif point == "equip":
                self.run(cmd, world)
            return
        if "stream" in how:
            self.start_stream(point, how["stream"], world)
            if point == "tick":
                anim.tick(lambda ctx: self._tick_stream(point, ctx))
            return

    def _import(self, rel):
        full = os.path.join(self.path, rel)
        name = "guy_item_%s_%s" % (self.id.replace("-", "_"), os.path.splitext(os.path.basename(rel))[0])
        spec = importlib.util.spec_from_file_location(name, full)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        return mod

    def run(self, cmd, world, data=None):
        env = self.env(world)
        if data:
            env["GUY_EVENT"] = json.dumps(data, default=str)
        try:
            subprocess.Popen(cmd, shell=True, cwd=self.path, env=env,
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=open(os.path.join(self.path, "stderr.log"), "a"))
        except Exception as e:  # noqa: BLE001
            log("run %s: %s" % (self.id, e))

    def start_stream(self, point, cmd, world):
        p = subprocess.Popen(cmd, shell=True, cwd=self.path, env=self.env(world), text=True,
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=open(os.path.join(self.path, "stderr.log"), "a"), bufsize=1)
        self.procs[point] = p
        self.stream_out[point] = None
        def reader():
            for line in p.stdout:
                line = line.strip()
                if line:
                    try:
                        self.stream_out[point] = json.loads(line)
                    except ValueError:
                        pass
        threading.Thread(target=reader, daemon=True).start()

    def _tick_stream(self, point, ctx):
        """Send the frame, draw the last reply. Reply: {"cells": [[x, y, "name"], ...],
        "text": [[col, row, "string", "ink"]], "say": "..."} in quarter cells."""
        p = self.procs.get(point)
        if not p or p.poll() is not None:
            return
        pose = getattr(ctx.guy, "last_pose", None) or {}
        frame = {"t": ctx.t, "dt": ctx.dt, "u": ctx.u, "x": pose.get("x"), "y": pose.get("y"),
                 "w": ctx.screen.w, "h": ctx.screen.h, "job": ctx.guy.job}
        try:
            p.stdin.write(json.dumps(frame) + "\n")
        except (BrokenPipeError, OSError):
            return
        out = self.stream_out.get(point)
        if not out:
            return
        ctx.guy._pending_stream_draw = getattr(ctx.guy, "_pending_stream_draw", [])
        ctx.guy._pending_stream_draw.append(out)

    def stop(self):
        for p in self.procs.values():
            try:
                p.terminate()
            except OSError:
                pass


def scan(where=None):
    if where is None:
        return scan(paths.STARTER) + scan(paths.ITEMS)
    out = []
    if not os.path.isdir(where):
        return out
    for name in sorted(os.listdir(where)):
        d = os.path.join(where, name)
        mf = os.path.join(d, "item.json")
        if os.path.isfile(mf):
            try:
                with open(mf) as f:
                    out.append(Item(d, json.load(f)))
            except ValueError as e:
                log("bad manifest %s: %s" % (mf, e))
    return out


def skills():
    """Skills bought from the talent graph live under talents/<id>/ and carry item.json too."""
    out = []
    for name in sorted(os.listdir(paths.TALENTS)) if os.path.isdir(paths.TALENTS) else []:
        d = os.path.join(paths.TALENTS, name)
        mf = os.path.join(d, "item.json")
        if os.path.isdir(d) and os.path.isfile(mf):
            with open(mf) as f:
                m = json.load(f)
            m["skill"] = True
            m.setdefault("id", name)
            out.append(Item(d, m))
    return out
