"""The widget: the guy's home pane, the bag, the talent graph, the forge queue
and the log. One process, one alternate screen, no network on the frame loop."""
import json
import os
import select
import signal
import sys
import termios
import threading
import time
import tty

from . import paths, state as S, rules, talents as T, items as I, sync, forge
from .anim import Anim
from .mascot import Guy
from .screen import CSI, P, Screen, Quad, named, named_bg, RARITY_INK, fg, bg
from .world import World
from .log import log

SYNC_EVERY = 600.0
KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT = b"\x1b[A", b"\x1b[B", b"\x1b[D", b"\x1b[C"


class App:
    def __init__(self, headless=False):
        paths.ensure()
        self.headless = headless
        self.st = S.load()
        self.st_mtime = S.mtime()
        self.world = World(self.st)
        self.page = "home"
        self.cursor = 0
        self.toasts = []           # (text, until, ink)
        self.status = ""
        self.forging = None        # thread
        self.syncing = None
        self.last_key_at = time.monotonic()
        self.idle_fired = False
        self.lock = threading.Lock()
        self.pending_events = []   # from the sync thread, fired on the main thread
        self.build()

    # ── building the scene from items ──
    def build(self):
        self.anim = Anim()
        self.guy = Guy(self.anim, self.st)
        self.world._st = self.st
        self.items = I.scan()
        self.skills = I.skills()
        self.by_id = {it.id: it for it in self.items + self.skills}
        for name in rules.category_names():
            rt = os.path.join(paths.CATEGORIES, name, "runtime.py")
            if os.path.exists(rt):
                try:
                    I.Item(os.path.join(paths.CATEGORIES, name), {"id": "cat_" + name, "attach": {"register": {"import": "runtime.py"}}}).attach(self.anim, self.world, self.guy)
                except Exception as e:  # noqa: BLE001
                    self.anim.fail("category " + name, e)
        self.st["equipped"] = [i for i in self.st.get("equipped", []) if i in self.by_id and not self.by_id[i].missing(self.st)]
        for it in self.skills:
            it.attach(self.anim, self.world, self.guy)
        for iid in self.st["equipped"]:
            self.by_id[iid].attach(self.anim, self.world, self.guy)
        if hasattr(self, "screen") and self.screen:
            self.guy.reset(self.screen)

    def reload(self):
        for it in getattr(self, "items", []) + getattr(self, "skills", []):
            it.stop()
        x, job = getattr(self.guy, "x", None), getattr(self.guy, "job", None)
        self.build()
        if x is not None:
            self.guy.x = self.guy.target = x

    def save(self):
        S.save(self.st)
        self.st_mtime = S.mtime()

    def toast(self, text, ink="text", seconds=5.0):
        self.toasts.append((text, time.monotonic() + seconds, ink))
        del self.toasts[:-4]

    # ── background work ──
    def start_sync(self, since=None):
        if self.syncing and self.syncing.is_alive():
            return
        def work():
            try:
                self.status = "syncing with github"
                fresh, happened = sync.run(since=since)
                with self.lock:
                    self.pending_events += [("event", ev) for ev in fresh]
                    self.pending_events += [("note", h) for h in happened]
                    self.pending_events.append(("synced", len(fresh)))
            except Exception as e:  # noqa: BLE001
                log("sync failed: %s" % e)
                with self.lock:
                    self.pending_events.append(("error", "sync failed: %s" % str(e)[:60]))
            finally:
                self.status = ""
        self.syncing = threading.Thread(target=work, daemon=True)
        self.syncing.start()

    def start_forge(self, job):
        if (self.forging and self.forging.is_alive()) or forge.busy():
            self.toast("the forge is busy. One thing at a time.", "peach")
            return
        def work():
            try:
                ok, msg = forge.run_job(job, on_status=lambda s: setattr(self, "status", s))
                with self.lock:
                    self.pending_events.append(("forged", (ok, msg, job)))
            except Exception as e:  # noqa: BLE001
                log("forge crashed: %s" % e)
                with self.lock:
                    self.pending_events.append(("error", "forge crashed: %s" % str(e)[:60]))
            finally:
                self.status = ""
        self.forging = threading.Thread(target=work, daemon=True)
        self.forging.start()
        self.guy.say("to the forge!", 3.0)

    def drain(self):
        with self.lock:
            evs, self.pending_events = self.pending_events, []
        if not evs:
            return
        reload_state = False
        for kind, payload in evs:
            if kind == "event":
                reload_state = True
                ev = payload
                self.guy.fire("pr_merged" if ev["kind"] == "pr" else "review", **ev)
                self.toast("%s %s#%s" % ("merged" if ev["kind"] == "pr" else "reviewed", ev["repo"].split("/")[-1], ev["number"]), "green")
            elif kind == "note":
                if payload.startswith("level"):
                    self.guy.fire("level_up", text=payload)
                    self.toast(payload, "yellow", 8.0)
                    notify("the guy reached %s" % payload, "a new thing waits at the forge")
                elif "drop" in payload:
                    self.guy.fire("drop", text=payload)
                    self.toast(payload + ". Press f to open it.", "mauve", 10.0)
                    notify("the guy found something", payload)
            elif kind == "synced":
                if payload == 0 and self.page == "home" and self.first_sync_done is False:
                    self.toast("synced. nothing new.", "subtext0", 3.0)
                self.first_sync_done = True
            elif kind == "forged":
                ok, msg, job = payload
                self.toast(msg, "green" if ok else "red", 8.0)
                self.st = S.load()
                self.reload()
                if ok:
                    self.guy.fire("forged", job=job)
                    self.guy.say("something new!", 4.0)
            elif kind == "error":
                self.toast(payload, "red", 8.0)
        if reload_state:
            self.st = S.load()
            self.reload()

    first_sync_done = False

    def watch_state_file(self):
        m = S.mtime()
        if m != self.st_mtime and not (self.syncing and self.syncing.is_alive()) and not (self.forging and self.forging.is_alive()):
            self.st = S.load()
            self.st_mtime = m
            self.reload()

    def watch_presence(self):
        try:
            with open(paths.PRESENCE) as f:
                pres = json.load(f)
        except (OSError, ValueError):
            return
        say = pres.pop("say", None)
        if say:
            self.guy.say(say["text"], max(0.5, say["until"] - time.time()))
            with open(paths.PRESENCE, "w") as f:
                json.dump(pres, f)

    # ── drawing ──
    def frame(self, s, dt):
        s.clear()
        self.screen = s
        if self.page == "home":
            self.draw_home(s, dt)
        elif self.page == "bag":
            self.draw_bag(s)
        elif self.page == "talents":
            self.draw_talents(s)
        elif self.page == "stats":
            self.draw_stats(s)
        elif self.page == "forge":
            self.draw_forge(s)
        elif self.page == "log":
            self.draw_log(s)
        elif self.page == "help":
            self.draw_help(s)
        elif self.page in self.anim.pages:
            title, draw, _ = self.anim.pages[self.page]
            self.header(s, title)
            try:
                draw(self.guy.ctx, s)
            except Exception as e:  # noqa: BLE001
                self.anim.fail("page " + self.page, e)
        else:
            self.page = "home"
        self.draw_toasts(s)
        if self.status:
            s.text(1, s.h - 1, " " + self.status + " ", named("crust"), named_bg("peach"))

    def header(self, s, title):
        st = self.st
        s.fill(0, 0, s.w, 1, " ", None, named_bg("crust"))
        left = " %s  ·  lv %d  ·  %s " % (st.get("name", "the guy"), st["level"], title)
        s.text(0, 0, left, named("text"), named_bg("crust"))
        right = " esc home  ?  help "
        s.text(s.w - len(right), 0, right, named("overlay1"), named_bg("crust"))

    def draw_home(self, s, dt):
        st = self.st
        self.guy.step(s, dt)
        pend = getattr(self.guy, "_pending_stream_draw", None)
        if pend:
            q = Quad()
            for out in pend:
                for c in out.get("cells", []):
                    try:
                        q.rect(int(c[0]), int(c[1]), self.guy.u, self.guy.u, P.get(c[2], P["text"]))
                    except (IndexError, TypeError, ValueError):
                        pass
                for t in out.get("text", []):
                    try:
                        s.text(int(t[0]), int(t[1]), str(t[2]), named(t[3] if len(t) > 3 else "text"))
                    except (IndexError, TypeError, ValueError):
                        pass
                if out.get("say"):
                    self.guy.say(str(out["say"]), 2.0)
            q.flush(s)
            self.guy._pending_stream_draw = []
        if s.h < 6 or s.w < 30:
            return
        # top bar: name, level, xp
        need = rules.xp_for_level(st["level"] + 1) - rules.xp_for_level(st["level"])
        have = st["xp"] - rules.xp_for_level(st["level"])
        frac = max(0.0, min(1.0, have / need if need else 1.0))
        label = " %s  lv %d " % (st.get("name", "the guy"), st["level"])
        s.text(1, 0, label, named("text"), named_bg("surface0"))
        bw = max(8, min(30, s.w - len(label) - 30))
        filled = int(bw * frac)
        s.text(1 + len(label) + 1, 0, "█" * filled + "░" * (bw - filled), named("green"))
        s.text(1 + len(label) + 2 + bw, 0, "%d/%d xp" % (have, need), named("overlay1"))
        # stats row
        row = "  ".join("%s %d" % (k[:3], v) for k, v in st["stats"].items())
        if len(row) < s.w - 2:
            s.text(s.w - len(row) - 1, 0, row, named("subtext0"))
        # unspent, queue, equipped
        notes = []
        if st["unspent"]["stat"]:
            notes.append(("%d stat point%s (s)" % (st["unspent"]["stat"], "" if st["unspent"]["stat"] == 1 else "s"), "yellow"))
        if st["unspent"]["talent"]:
            notes.append(("%d talent point%s (t)" % (st["unspent"]["talent"], "" if st["unspent"]["talent"] == 1 else "s"), "mauve"))
        nq = len(sync.pending_jobs())
        if nq:
            notes.append(("%d unopened thing%s (f)" % (nq, "" if nq == 1 else "s"), "peach"))
        x = 1
        for text, ink in notes:
            s.text(x, 1, text, named(ink))
            x += len(text) + 3
        eq = [self.by_id[i].name for i in st["equipped"] if i in self.by_id]
        if eq and s.h > 8:
            line = "wearing: " + ", ".join(eq)
            s.text(1, 2, line[:s.w - 2], named("overlay1"))
        # hint chips
        hint = " b bag  t talents  s stats  f forge  l log  ? help  q quit "
        for ch, (fn, help_) in self.anim.keys.items():
            if help_:
                hint += " %s %s " % (ch, help_)
        if s.w > len(hint) + 2:
            s.text(1, s.h - 1, hint, named("overlay0"), named_bg("crust"))

    def draw_toasts(self, s):
        now = time.monotonic()
        self.toasts = [t for t in self.toasts if t[1] > now]
        y = 3 if self.page == "home" else 2
        for text, _, ink in self.toasts[-3:]:
            s.text(s.w - len(text) - 2, y, " " + text + " ", named("crust"), named_bg(ink))
            y += 1

    def all_items(self):
        return self.skills + self.items

    def draw_bag(self, s):
        self.header(s, "bag")
        st = self.st
        rows = self.all_items()
        if not rows:
            s.text(2, 2, "the bag is empty. Merge something.", named("subtext0"))
            return
        self.cursor = max(0, min(self.cursor, len(rows) - 1))
        listw = min(46, s.w // 2)
        s.text(2, 1, "%d/%d slots" % (len(st["equipped"]), st["slots"]), named("overlay1"))
        top = max(0, self.cursor - (s.h - 5))
        for i, it in enumerate(rows[top:top + s.h - 4]):
            y = 2 + i
            idx = top + i
            missing = it.missing(st)
            on = it.id in st["equipped"] or it.skill
            mark = "◆" if on else ("◇" if not missing else "·")
            ink = RARITY_INK.get(it.rarity, "text") if not missing else "overlay0"
            line = "%s %s" % (mark, it.name)
            if it.skill:
                line += "  (skill)"
            s.text(3, y, line[:listw - 2], named(ink), named_bg("surface0") if idx == self.cursor else None)
        it = rows[self.cursor]
        x = listw + 3
        w = s.w - x - 2
        if w < 10:
            return
        s.text(x, 2, it.name, named(RARITY_INK.get(it.rarity, "text")))
        s.text(x, 3, "%s %s" % (it.rarity, it.category), named("overlay1"))
        y = 5
        for line in wrap(it.m.get("flavor", ""), w):
            s.text(x, y, line, named("subtext1")); y += 1
        y += 1
        req = it.m.get("requires", {})
        if req and not it.skill:
            missing = it.missing(st)
            s.text(x, y, "requires", named("overlay1")); y += 1
            parts = []
            if req.get("level"):
                parts.append(("level %d" % req["level"], "level %d" % req["level"] in missing))
            for k, v in req.get("stats", {}).items():
                parts.append(("%s %d" % (k, v), "%s %d" % (k, v) in missing))
            for text, bad in parts:
                s.text(x + 2, y, text, named("red" if bad else "green")); y += 1
            y += 1
        att = it.m.get("attach", {})
        if att:
            s.text(x, y, "does", named("overlay1")); y += 1
            for point, how in list(att.items())[:6]:
                desc = how.get("help") or next(iter(how.values()))
                s.text(x + 2, y, ("%s: %s" % (point, desc))[:w - 2], named("subtext0")); y += 1
        hint = " enter equip/unequip  ↑↓ move  esc back "
        if it.skill:
            hint = " skills are always on  esc back "
        s.text(1, s.h - 1, hint, named("overlay0"), named_bg("crust"))

    def bag_key(self, key):
        rows = self.all_items()
        if not rows:
            return
        if key in (KEY_UP, b"k"):
            self.cursor -= 1
        elif key in (KEY_DOWN, b"j"):
            self.cursor += 1
        elif key in (b"\r", b"\n", b" "):
            it = rows[max(0, min(self.cursor, len(rows) - 1))]
            if it.skill:
                return
            st = self.st
            if it.id in st["equipped"]:
                st["equipped"].remove(it.id)
                self.save(); self.reload(); self.guy.fire("unequip", item=it.id)
                self.toast("took off %s" % it.name, "subtext0")
            else:
                missing = it.missing(st)
                if missing:
                    self.toast("needs " + ", ".join(missing), "red")
                elif len(st["equipped"]) >= st["slots"]:
                    self.toast("no free slot", "red")
                else:
                    st["equipped"].append(it.id)
                    S.remember(st, "equip", "put on %s" % it.name)
                    self.save(); self.reload(); self.guy.fire("equip", item=it.id)
                    self.toast("wearing %s" % it.name, "green")

    def draw_stats(self, s):
        self.header(s, "stats")
        st = self.st
        stats = list(st["stats"].items())
        self.cursor = max(0, min(self.cursor, len(stats) - 1))
        s.text(2, 2, "%d point%s to spend" % (st["unspent"]["stat"], "" if st["unspent"]["stat"] == 1 else "s"),
               named("yellow" if st["unspent"]["stat"] else "overlay1"))
        for i, (k, v) in enumerate(stats):
            y = 4 + i
            bar = "█" * min(v, s.w - 24)
            s.text(3, y, "%-6s %3d " % (k, v), named("text"), named_bg("surface0") if i == self.cursor else None)
            s.text(15, y, bar, named("sky" if i == self.cursor else "surface2"))
        s.text(1, s.h - 1, " enter spend a point  ↑↓ move  esc back ", named("overlay0"), named_bg("crust"))

    def stats_key(self, key):
        stats = list(self.st["stats"])
        if key in (KEY_UP, b"k"):
            self.cursor -= 1
        elif key in (KEY_DOWN, b"j"):
            self.cursor += 1
        elif key in (b"\r", b"\n", b" "):
            k = stats[max(0, min(self.cursor, len(stats) - 1))]
            if T.spend_stat(self.st, k):
                self.save()
                self.toast("+1 %s" % k, "green", 2.0)
            else:
                self.toast("no points to spend", "red", 2.0)

    def draw_talents(self, s):
        self.header(s, "talents")
        st = self.st
        nodes = T.load_all()
        if not nodes:
            s.text(2, 2, "no talent graph. Odd.", named("red"))
            return
        owned = set(st["owned_talents"])
        buyable = set(T.buyable(nodes, owned))
        ids = sorted(nodes, key=lambda i: (nodes[i].get("pos", [0, 0])[1], nodes[i].get("pos", [0, 0])[0]))
        if not hasattr(self, "tcursor") or self.tcursor not in nodes:
            self.tcursor = next(iter(buyable), "root")
        s.text(2, 1, "%d talent point%s" % (st["unspent"]["talent"], "" if st["unspent"]["talent"] == 1 else "s"),
               named("mauve" if st["unspent"]["talent"] else "overlay1"))
        panelw = min(34, s.w // 3)
        gw = s.w - panelw - 2
        cx, cy = gw // 2, (s.h - 2) // 2 + 1
        sx, sy = 9, 3
        placed = {}
        for i in ids:
            n = nodes[i]
            px, py = n.get("pos", [0, 0])
            x, y = cx + px * sx, cy + py * sy
            placed[i] = (x, y)
        # edges
        for i in ids:
            n = nodes[i]
            p = n.get("parent")
            if p in placed and i in placed:
                (x1, y1), (x2, y2) = placed[p], placed[i]
                steps = max(abs(x2 - x1), abs(y2 - y1))
                for k in range(1, steps):
                    ex = x1 + (x2 - x1) * k // steps
                    ey = y1 + (y2 - y1) * k // steps
                    if 1 <= ey < s.h - 1 and 0 <= ex < gw:
                        s.set(ex, ey, "·", named("surface2" if not (i in owned) else "overlay1"))
        for i in ids:
            n = nodes[i]
            x, y = placed[i]
            name = n.get("name", i)
            label = name[:sx * 2 - 2]
            if i in owned:
                ink, bgk = "text", "surface1"
            elif i in buyable:
                ink, bgk = RARITY_INK["rare"] if n.get("kind") == "skill" else "green", "surface0"
            else:
                ink, bgk = "overlay0", None
            if i == self.tcursor:
                bgk = "mauve"; ink = "crust"
            if 1 <= y < s.h - 1:
                s.text(max(0, x - len(label) // 2), y, " %s " % label, named(ink), named_bg(bgk) if bgk else None)
        # panel
        n = nodes[self.tcursor]
        x = gw + 2
        s.fill(x - 1, 1, 1, s.h - 2, "│", named("surface1"))
        s.text(x, 2, n.get("name", self.tcursor), named("text"))
        state = "owned" if self.tcursor in owned else ("cost %d" % n.get("cost", 1) if self.tcursor in buyable else "locked")
        s.text(x, 3, "%s · %s" % (n.get("kind", "passive"), state), named("overlay1"))
        y = 5
        for line in wrap(n.get("hint", ""), panelw - 1):
            s.text(x, y, line, named("subtext1")); y += 1
        eff = n.get("effect", {})
        if eff:
            y += 1
            for k, v in eff.items():
                s.text(x, y, ("%s: %s" % (k, json.dumps(v)))[:panelw - 1], named("subtext0")); y += 1
        s.text(1, s.h - 1, " enter learn  ←↑↓→ move  esc back ", named("overlay0"), named_bg("crust"))

    def talents_key(self, key):
        nodes = T.load_all()
        if not nodes:
            return
        cur = nodes.get(self.tcursor) or nodes["root"]
        cx, cy = cur.get("pos", [0, 0])
        d = {KEY_UP: (0, -1), KEY_DOWN: (0, 1), KEY_LEFT: (-1, 0), KEY_RIGHT: (1, 0),
             b"k": (0, -1), b"j": (0, 1), b"h": (-1, 0), b"l": (1, 0)}.get(key)
        if d:
            best, bd = None, 1e9
            for i, n in nodes.items():
                if i == self.tcursor:
                    continue
                px, py = n.get("pos", [0, 0])
                dx, dy = px - cx, py - cy
                if dx * d[0] + dy * d[1] <= 0:
                    continue
                dist = (dx * 1.0) ** 2 + (dy * 2.5) ** 2 - 0.5 * abs(dx * d[0] + dy * d[1])
                if dist < bd:
                    best, bd = i, dist
            if best:
                self.tcursor = best
        elif key in (b"\r", b"\n", b" "):
            ok, msg, job = T.buy(self.st, self.tcursor)
            self.toast(msg, "green" if ok else "red")
            if ok:
                self.save()
                self.guy.fire("talent", node=self.tcursor)
                if job:
                    self.toast("the graph wants to grow. Press f.", "mauve", 8.0)

    def draw_forge(self, s):
        self.header(s, "forge")
        jobs = sync.pending_jobs()
        busy = (self.forging and self.forging.is_alive()) or forge.busy()
        if not jobs:
            s.text(2, 2, "nothing to open. Merge a PR, review one, or learn a talent.", named("subtext0"))
        self.cursor = max(0, min(self.cursor, max(0, len(jobs) - 1)))
        for i, j in enumerate(jobs[:s.h - 5]):
            sp = j["spec"]
            ink = RARITY_INK.get(sp.get("rarity"), "text")
            line = "%s %-9s %-7s %s" % ("▸" if i == self.cursor else " ", sp.get("rarity", "?"), sp.get("scope", ""), j.get("note", j["id"]))
            s.text(2, 2 + i, line[:s.w - 4], named(ink), named_bg("surface0") if i == self.cursor else None)
        if jobs:
            j = jobs[self.cursor]
            sp = j["spec"]
            y = min(len(jobs), s.h - 5) + 3
            s.text(2, y, "a %s %s in %s · mood %s · %s%s" % (
                sp.get("rarity"), sp.get("scope"), sp.get("category"), sp.get("mood"), sp.get("constraint"),
                (" · twist: " + sp["twist"]) if sp.get("twist") else "")[:s.w - 4], named("subtext0"))
            s.text(2, y + 1, ("theme: " + ", ".join(sp.get("theme", [])))[:s.w - 4], named("overlay1"))
        s.text(1, s.h - 1, (" the forge is busy " if busy else " enter open it (one claude session)  ↑↓ move  esc back "),
               named("overlay0"), named_bg("crust"))

    def forge_key(self, key):
        jobs = sync.pending_jobs()
        if key in (KEY_UP, b"k"):
            self.cursor -= 1
        elif key in (KEY_DOWN, b"j"):
            self.cursor += 1
        elif key in (b"\r", b"\n", b" ") and jobs:
            self.start_forge(jobs[max(0, min(self.cursor, len(jobs) - 1))])

    def draw_log(self, s):
        self.header(s, "log")
        hist = self.st.get("history", [])
        rows = hist[-(s.h - 3):]
        inks = {"pr": "green", "review": "sky", "level": "yellow", "drop": "mauve", "forge": "peach", "talent": "lavender"}
        for i, h in enumerate(rows):
            s.text(2, 2 + i, h["t"], named("overlay0"))
            s.text(20, 2 + i, h["text"][:s.w - 22], named(inks.get(h["kind"], "subtext0")))
        errs = self.anim.errors
        if errs:
            y = s.h - 2 - len(errs[-3:])
            for e in errs[-3:]:
                s.text(2, y, ("! " + e)[:s.w - 3], named("red")); y += 1

    def draw_help(self, s):
        self.header(s, "help")
        lines = [
            "the guy grows when you merge a pull request or review one.",
            "every event gives xp and a random stat or three. some drop things.",
            "levels give stat points (s) and talent points (t), and a guaranteed thing.",
            "things arrive unopened. open them at the forge (f): one claude session each.",
            "an item you cannot use yet still sits in the bag (b). requirements in red.",
            "", "keys on the home page:",
            "  b bag   t talents   s stats   f forge   l log   ? help   q quit   S sync now",
        ]
        for ch, (fn, help_) in self.anim.keys.items():
            lines.append("  %s %s" % (ch, help_ or "(an item)"))
        for i, line in enumerate(lines[:s.h - 3]):
            s.text(2, 2 + i, line[:s.w - 4], named("subtext1"))

    # ── keys ──
    def key(self, key):
        self.last_key_at = time.monotonic()
        self.idle_fired = False
        if key in (b"q", b"Q", b"\x03", b"\x04"):
            return "quit"
        if key == b"\x1b":
            self.page = "home"; self.cursor = 0
            return
        if self.page == "home":
            ch = key.decode("utf-8", "ignore")
            if ch in self.anim.keys and ch not in "btsflq?S":
                fn, _ = self.anim.keys[ch]
                try:
                    fn(self.guy.ctx)
                except Exception as e:  # noqa: BLE001
                    self.anim.fail("key " + ch, e)
                    self.toast("that item misfired: %s" % str(e)[:40], "red")
                return
            if ch == "b": self.page = "bag"; self.cursor = 0
            elif ch == "t": self.page = "talents"
            elif ch == "s": self.page = "stats"; self.cursor = 0
            elif ch == "f": self.page = "forge"; self.cursor = 0
            elif ch == "l": self.page = "log"
            elif ch == "?": self.page = "help"
            elif ch == "S": self.start_sync(); self.toast("syncing", "subtext0", 2.0)
            elif ch in self.anim.pages: self.page = ch
            return
        if self.page == "bag": self.bag_key(key)
        elif self.page == "stats": self.stats_key(key)
        elif self.page == "talents": self.talents_key(key)
        elif self.page == "forge": self.forge_key(key)
        elif self.page in self.anim.pages:
            _, _, keys = self.anim.pages[self.page]
            if keys:
                try:
                    keys(self.guy.ctx, key)
                except Exception as e:  # noqa: BLE001
                    self.anim.fail("page key " + self.page, e)

    def housekeeping(self, now):
        self.drain()
        self.watch_state_file()
        self.watch_presence()
        if now - self.last_sync > SYNC_EVERY:
            self.last_sync = now
            self.start_sync()
        if not self.idle_fired and now - self.last_key_at > 300:
            self.idle_fired = True
            self.guy.fire("idle")

    last_sync = 0.0


def notify(title, body):
    """A desktop notification, on macOS. Silent anywhere else."""
    import subprocess
    if sys.platform != "darwin":
        return
    script = 'display notification "%s" with title "%s"' % (body.replace('"', "'"), title.replace('"', "'"))
    try:
        subprocess.Popen(["osascript", "-e", script], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def wrap(text, w):
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > w and line:
            out.append(line); line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out


def term_size():
    try:
        w, h = os.get_terminal_size(sys.stdout.fileno())
    except OSError:
        w, h = 80, 24
    return max(8, w), max(4, h)


def write_presence(app):
    try:
        with open(paths.PRESENCE, "w") as f:
            json.dump({"pane": app.world.pane_id, "session": app.world.session, "pid": os.getpid(),
                       "since": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    except OSError:
        pass


def run(fps_override=None, no_sync=False):
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    out = sys.stdout
    resized = [False]

    def on_winch(*_):
        resized[0] = True

    prev_winch = signal.signal(signal.SIGWINCH, on_winch)
    tty.setcbreak(fd)
    out.write(CSI + "?1049h" + CSI + "?25l" + CSI + "?7l" + CSI + "2J")
    out.flush()
    app = App()
    write_presence(app)
    try:
        w, h = term_size()
        screen = Screen(w, h)
        app.screen = screen
        app.guy.reset(screen)
        if not no_sync:
            app.last_sync = time.monotonic()
            app.start_sync()
        last = time.monotonic()
        while True:
            if resized[0]:
                resized[0] = False
                w, h = term_size()
                screen = Screen(w, h)
                app.screen = screen
                out.write(CSI + "2J")
                app.guy.reset(screen)
                last = time.monotonic()
            now = time.monotonic()
            dt = min(0.12, now - last)
            last = now
            app.housekeeping(now)
            app.frame(screen, dt)
            screen.flush(out)
            fps = max(4.0, min(60.0, fps_override or app.guy.fps))
            deadline = now + 1.0 / fps
            key = b""
            while True:
                left = deadline - time.monotonic()
                if left <= 0:
                    break
                r, _, _ = select.select([fd], [], [], left)
                if r:
                    key = os.read(fd, 32)
                    break
            if key and app.key(key) == "quit":
                return
    except KeyboardInterrupt:
        pass
    finally:
        for it in app.items + app.skills:
            it.stop()
        out.write(CSI + "?7h" + CSI + "0m" + CSI + "?25h" + CSI + "?1049l")
        out.flush()
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        signal.signal(signal.SIGWINCH, prev_winch)


def boot_test(frames=300):
    """Headless. Exit code 0 means the widget boots and every page draws."""
    import io
    app = App(headless=True)
    s = Screen(120, 40)
    app.screen = s
    app.guy.reset(s)
    sink = io.StringIO()
    # equip every usable item so their code runs
    for it in app.items:
        if not it.missing(app.st) and it.id not in app.st["equipped"] and len(app.st["equipped"]) < 99:
            it.attach(app.anim, app.world, app.guy)
    for i in range(frames):
        app.frame(s, 1 / 30)
        s.flush(sink)
        if i == 40:
            for ev in ("pr_merged", "review", "level_up", "drop", "equip", "unequip", "idle", "forged", "talent"):
                app.guy.fire(ev, text="boot test", kind="pr", repo="x/y", number=1)
        if i == 60:
            app.guy._next(s)
    for page in ["bag", "talents", "stats", "forge", "log", "help"] + list(app.anim.pages):
        app.page = page
        for _ in range(3):
            app.frame(s, 1 / 30)
            s.flush(sink)
    for it in app.items + app.skills:
        it.stop()
    errs = list(app.anim.errors)
    for e in errs:
        print("error:", e)
    print("boot test: %d frames, %d items, %d skills, %d idle jobs, %d layers, %d keys, %d pages, %d errors" % (
        frames, len(app.items), len(app.skills), len(app.anim.idle_jobs), len(app.anim.layers),
        len(app.anim.keys), len(app.anim.pages), len(errs)))
    return 1 if errs else 0
