"""Fable. Descended from the claude-idle mascot, with his jobs, layers and
reactions moved into registries that items can extend."""
import math
import random
from .screen import P, Quad, named
from . import screen as SC
from .anim import Ctx
from . import clock

CLAY = "clay"
BODY = "..############.."
NUBS = "################"
EYES_SHUT = BODY
LEGS_STAND = "...#.#....#.#..."
LEGS_STRIDE = "..#...#..#...#.."
LEGS_TUCK = "....##....##...."
EYE_L, EYE_R = 4, 11
MASCOT_W = 16
MASCOT_H = 5

LAPTOP = ("#########", "#ccccccc#", "#ccccccc#", "kkkkkkkkk")
MUG = ("####h", "#bb#h", "####.")
BOOK = ("#########", "#ppp#ppp#", "#########")
BUBBLE = (".#######.", "#########", ".#######.")
ZED = ("###", ".#.", "###")
BALL = ("##",)
INK = {"#": "overlay1", "c": "crust", "k": "surface2", "b": "maroon",
       "h": "rosewater", "p": "subtext1", "s": "sky"}
CODE_INK = ("green", "teal", "sky", "mauve", "yellow", "peach")
BALL_INK = ("mauve", "sky", "green")
STEP_HOLD = (0.14, 0.22)
HOP_RISE = 0.45
LAND_HOLD = 0.16


def face_row(e):
    row = list(BODY)
    row[EYE_L + e] = "."
    row[EYE_R + e] = "."
    return "".join(row)


class Guy:
    fps = 30

    def __init__(self, anim, state):
        self.anim = anim
        self.state = state
        self.ctx = Ctx(self)
        self.screen = None
        self.store = {}
        self.caption_override = None
        self.playing = []       # running reaction generators
        self.last_pose = {}
        self.bubble = None      # (text, until)
        self.t = 0.0
        self.dt = 1 / 30
        self._register_builtin_jobs()

    def _register_builtin_jobs(self):
        # Only napping is built in. The laptop, the mug, the book and the balls
        # are starter items in starter/, and thinking is a starter talent.
        a = self.anim
        a.idle_job("naps", 1, "recharging", self._naps, eye=0)
        a.reaction("level_up", self._level_up)
        a.reaction("drop", self._drop_glow)

    # ── built-in reactions ──
    def _level_up(self, ctx, data):
        """Two seconds of sparks from the head, a hop, and a word."""
        u = self.u
        self.say(data.get("text", "level up") + "!", 5.0)
        t0 = self.t
        next_burst = t0
        while self.t - t0 < 2.4:
            if self.t >= next_burst:
                next_burst = self.t + 0.18
                x = int(self.x * 2)
                self._burst(x + 8 * u, self.last_pose.get("y", 0) - u, 6,
                            ("yellow", "peach", "rosewater", "green", "sky"))
            self._sparks(ctx.q)
            yield
        while self.sparks:
            self._sparks(ctx.q)
            yield

    def _drop_glow(self, ctx, data):
        """Something fell. A short shimmer at the feet."""
        u = self.u
        t0 = self.t
        while self.t - t0 < 1.5:
            f = 1.0 - (self.t - t0) / 1.5
            x = int(self.x * 2)
            fy = self.last_pose.get("y", 0) + 5 * u
            for i in range(0, 16 * u, u):
                if (i // u + int(self.t * 12)) % 3 == 0:
                    self._block(ctx.q, x + i, fy, self._fade("mauve", f))
            yield

    # ── setup ──
    def reset(self, s):
        self.screen = s
        self.t = 0.0
        self.blink_at = random.uniform(2.0, 5.0)
        self.glance_at = random.uniform(2.0, 4.0)
        self.glance = 0
        self.k = self._scale(s)
        self.u = 2 * max(1, self.k)
        self.job = self._pick_job()
        self.dur = random.uniform(12.0, 16.0)
        self.t0 = 0.0
        self.mode = "do"
        self.x = float(self._spot(s))
        self.target = self.x
        self.leg_i = 0
        self.leg_t = 0.0
        self.hop_x0 = self.x
        self.hop_t0 = 0.0
        self.hop_dur = 1.0
        self.dust = []
        self.sparks = []
        self.store = {}
        self.face_dir = 1
        self.hour = clock.now()["hour"]

    def _pick_job(self):
        jobs = self.anim.idle_jobs
        if not jobs:
            return None
        names = list(jobs)
        weights = [max(0, jobs[n]["weight"]) for n in names]
        if sum(weights) == 0:
            return random.choice(names)
        choice = random.choices(names, weights)[0]
        if choice == getattr(self, "job", None) and len(names) > 1:
            choice = random.choices(names, weights)[0]
        return choice

    def _scale(self, s):
        for k in (3, 2, 1):
            if s.w >= 35 * k and s.h >= 9 * k + 6:
                return k
        return 0

    def _spot(self, s):
        k = max(1, self.k)
        lo, hi = 8 * k, s.w - 27 * k
        return random.randint(lo, hi) if hi > lo else max(0, lo)

    # ── painting helpers, used by Ctx too ──
    def _cell(self, q, x, y, name):
        q.rect(x, y, self.u, self.u, P.get(name, P["text"]))

    def _block(self, q, x, y, rgb):
        q.rect(x, y, self.u, self.u, rgb)

    def _grid(self, q, x, y, rows, ink=None):
        u = self.u
        for gy, row in enumerate(rows):
            by = y + gy * u
            for gx, ch in enumerate(row):
                if ch == ".":
                    continue
                q.rect(x + gx * u, by, u, u, P.get(CLAY if ink is None else ink.get(ch, CLAY), P["text"]))

    def _fade(self, name, f):
        r, g, b = P[name]
        br, bgc, bb = P["base"]
        return (int(br + (r - br) * f), int(bgc + (g - bgc) * f), int(bb + (b - bb) * f))

    def _mascot(self, q, x, y, eye=0, lean=0, legs=LEGS_STAND, squash=False, shut=False):
        u = self.u
        if shut or self.blink_at < self.t < self.blink_at + 0.15:
            face = EYES_SHUT
        else:
            face = face_row(eye)
        tilt = lean * (u // 2)
        pose = {"x": x, "y": y, "eye": eye, "lean": lean, "squash": squash, "shut": shut, "u": u}
        for z, name, draw in self.anim.layers:
            if z < 0 and draw:
                self._safe(draw, "layer " + name, self.ctx, q, pose)
        if squash:
            self._grid(q, x + tilt, y + u, (face,))
            self._grid(q, x, y + 2 * u, (NUBS, BODY, legs))
        else:
            self._grid(q, x + tilt, y, (BODY, face))
            self._grid(q, x, y + 2 * u, (NUBS, BODY, legs))
        for z, name, draw in self.anim.layers:
            if z >= 0 and draw:
                self._safe(draw, "layer " + name, self.ctx, q, pose)
        self.last_pose = pose

    def _safe(self, fn, where, *args):
        try:
            return fn(*args)
        except Exception as e:  # noqa: BLE001
            self.anim.fail(where, e)
            return None

    def _look(self, base):
        return self.glance if self.glance else base

    def _burst(self, x, y, n, inks):
        for _ in range(n):
            self.sparks.append([float(x), float(y), random.uniform(-2.5, 2.5) * self.u,
                                random.uniform(-8.0, -5.0) * self.u, 0.0, random.choice(inks), float(y)])

    def _sparks(self, q):
        for p in self.sparks:
            p[3] += 15.0 * self.u * self.dt
            p[0] += p[2] * self.dt
            p[1] += p[3] * self.dt
            p[4] += self.dt
            self._block(q, int(p[0]), int(p[1]), self._fade(p[5], max(0.1, 1.0 - p[4] / 1.1)))
        self.sparks = [p for p in self.sparks if p[4] < 1.1 and p[1] < p[6]]

    # ── built-in jobs. Signature: (ctx, q, x, y, floor_y) in quarter cells ──
    def _types(self, c, q, x, y, fy):
        u, k, st = self.u, self.k, self.store
        st.setdefault("code", [[None] * 7, [None] * 7])
        st.setdefault("col", 0); st.setdefault("lines", 0); st.setdefault("type_at", 0.0); st.setdefault("flash", 0.0)
        lx, ly = x + 18 * u, fy - 4 * u
        self._grid(q, lx, ly, LAPTOP, INK)
        if self.t > st["type_at"]:
            st["type_at"] = self.t + 0.13
            if st["col"] >= 7:
                st["code"][0] = list(st["code"][1]); st["code"][1] = [None] * 7
                st["col"] = 0; st["lines"] += 1
                if st["lines"] % 4 == 0:
                    st["flash"] = 0.4
                    self._burst(lx + 4 * u, ly - u, 7, ("green", "teal", "yellow"))
            else:
                st["code"][1][st["col"]] = random.choice(CODE_INK); st["col"] += 1
        st["flash"] = max(0.0, st["flash"] - self.dt)
        won = st["flash"] > 0.0
        for r in (0, 1):
            for col in range(7):
                name = "green" if won else st["code"][r][col]
                if name:
                    self._cell(q, lx + (col + 1) * u, ly + (r + 1) * u, name)
        if not won and int(self.t * 4) % 2:
            self._cell(q, lx + (st["col"] + 1) * u, ly + 2 * u, "text")
        self._sparks(q)
        bob = k if int(self.t * 6) % 2 else 0
        self._mascot(q, x, y - k if won else y + bob, self._look(1))

    def _coffee(self, c, q, x, y, fy):
        u, st = self.u, self.store
        st.setdefault("puffs", []); st.setdefault("puff_at", 0.0)
        sip = self.t % 4.0 > 3.4
        mx, my = x + 18 * u, fy - 3 * u - (u if sip else 0)
        self._grid(q, mx, my, MUG, INK)
        if not sip and self.t > st["puff_at"]:
            st["puff_at"] = self.t + 0.45
            st["puffs"].append([float(mx + u), float(my - u), 0.0])
        for p in st["puffs"]:
            p[1] -= 3.0 * u * self.dt; p[2] += self.dt
            wob = math.sin(p[2] * 3.0) * 1.5 * u
            self._block(q, int(p[0] + wob), int(p[1]), self._fade("subtext0", max(0.12, 1.0 - p[2] / 2.4)))
        st["puffs"] = [p for p in st["puffs"] if p[2] < 2.4]
        self._mascot(q, x, y, self._look(1), shut=sip)

    def _reads(self, c, q, x, y, fy):
        u, st = self.u, self.store
        st.setdefault("read_i", 0); st.setdefault("read_at", 0.0); st.setdefault("turn", None); st.setdefault("idea_at", 4.0)
        bx, by = x + 18 * u, fy - 3 * u
        self._grid(q, bx, by, BOOK, INK)
        if st["turn"] is None and self.t > st["read_at"]:
            st["read_at"] = self.t + 0.38; st["read_i"] += 1
            if st["read_i"] > 5:
                st["read_i"] = 0; st["turn"] = 0.0
        for i in range(6):
            gx = 1 + i if i < 3 else 2 + i
            here = i == st["read_i"] and st["turn"] is None
            self._cell(q, bx + gx * u, by + u, "text" if here else "subtext0")
        if st["turn"] is not None:
            st["turn"] += self.dt / 0.45
            if st["turn"] >= 1.0:
                st["turn"] = None
            else:
                f = st["turn"]
                self._cell(q, int(bx + (6.0 - 4.0 * f) * u), int(by + u - 2.0 * u * 4.0 * f * (1.0 - f)), "text")
        if self.t > st["idea_at"]:
            st["idea_at"] = self.t + random.uniform(6.0, 9.0)
            self._burst(x + 8 * u, y - u, 5, ("yellow", "peach", "rosewater"))
        self._sparks(q)
        self._mascot(q, x, y, self._look(0 if st["read_i"] < 3 else 1))

    def _juggles(self, c, q, x, y, fy):
        u = self.u
        span = 1.15
        left, right = x + u, x + 14 * u
        hy = y + 2 * u
        peak = 5.0 * u
        catch = False
        top_x, top_y = x, 1e9
        for i in range(3):
            tt = self.t + i * span / 3.0
            n = int(tt / span)
            f = tt / span - n
            a, b = (left, right) if n % 2 == 0 else (right, left)
            bx = a + (b - a) * f
            by = hy - peak * 4.0 * f * (1.0 - f)
            if f > 0.90:
                catch = True
            if by < top_y:
                top_y, top_x = by, bx
            self._grid(q, int(bx), int(by), BALL, {"#": BALL_INK[i]})
        self._mascot(q, x, y, self._look(1 if top_x > x + 8 * u else -1), squash=catch)

    def _thinks(self, c, q, x, y, fy):
        u = self.u
        bx, by = x + 12 * u, y - 4 * u
        self._grid(q, bx, by, BUBBLE, {"#": "surface1"})
        pulse = 0.55 + 0.45 * math.sin(self.t * 3.0)
        r, g, b = P[CLAY]; br, bgc, bb = P["surface1"]
        self._block(q, bx + 2 * u, by + u, (int(br + (r - br) * pulse), int(bgc + (g - bgc) * pulse), int(bb + (b - bb) * pulse)))
        lit = int(self.t * 3.0) % 3
        for i in range(3):
            self._cell(q, bx + (4 + i) * u, by + u, "text" if i == lit else "overlay0")
        self._cell(q, bx + u, by + 3 * u, "surface1")
        self._cell(q, bx, by + 4 * u, "surface1")
        self._mascot(q, x, y, self._look(1))

    def _naps(self, c, q, x, y, fy):
        u, st = self.u, self.store
        st.setdefault("zzz", []); st.setdefault("zzz_at", 0.0)
        if self.t > st["zzz_at"]:
            st["zzz_at"] = self.t + 1.2
            st["zzz"].append([float(x + 16 * u), float(y - u), 0.0])
        for z in st["zzz"]:
            z[1] -= 3.0 * u * self.dt; z[2] += self.dt
            self._grid(q, int(z[0] + z[2] * 2.0 * u), int(z[1]), ZED, {"#": "lavender"})
        st["zzz"] = [z for z in st["zzz"] if z[2] < 3.0]
        self._mascot(q, x, y, shut=True)

    # ── moving ──
    def _walk(self, q, y):
        way = 1.0 if self.target > self.x else -1.0
        self.x += way * 16.0 * self.dt
        self.leg_t += self.dt
        if self.leg_t > STEP_HOLD[self.leg_i]:
            self.leg_t = 0.0; self.leg_i ^= 1
        legs = LEGS_STRIDE if self.leg_i else LEGS_STAND
        lean = int(way)
        self._mascot(q, int(self.x * 2), y, eye=lean, lean=lean, legs=legs)
        if abs(self.target - self.x) < 0.75:
            self.x = self.target; self.mode = "do"; self.t0 = self.t; self.store = {}

    def _hop(self, q, y):
        u = self.u
        p = (self.t - self.hop_t0) / self.hop_dur
        if p >= 1.0:
            self.x = self.target; self.mode = "land"; self.t0 = self.t
            for side in (2, 13):
                self.dust.append([float(int(self.x * 2) + side * u), float(y + 4 * u), 0.0])
            return
        if p < HOP_RISE:
            rise = math.sin(p / HOP_RISE * math.pi / 2)
        else:
            rise = 1.0 - ((p - HOP_RISE) / (1.0 - HOP_RISE)) ** 3
        self.x = self.hop_x0 + (self.target - self.hop_x0) * p
        lean = 1 if self.target > self.hop_x0 else -1
        self._mascot(q, int(self.x * 2), int(y - rise * 3 * u), eye=lean, lean=lean, legs=LEGS_TUCK)

    def _land(self, q, y):
        self._mascot(q, int(self.x * 2), y, legs=LEGS_STAND, squash=True, shut=True)
        if self.t - self.t0 > LAND_HOLD:
            self.mode = "do"; self.t0 = self.t; self.store = {}

    # ── reactions ──
    def fire(self, event, **data):
        """Fire a named moment. Items registered on it play."""
        for play in self.anim.reactions.get(event, []):
            gen = self._safe(play, "reaction " + event, self.ctx, data)
            if gen is not None and hasattr(gen, "send"):
                self.playing.append((event, gen))

    def say(self, text, seconds=4.0):
        self.bubble = (text, self.t + seconds)

    # ── the frame ──
    def _caption(self, s, y):
        cap = self.caption_override
        if cap is None and self.job in self.anim.idle_jobs:
            cap = self.anim.idle_jobs[self.job]["caption"]
        if cap and y <= s.h - 2 and len(cap) < s.w:
            s.text((s.w - len(cap)) // 2, y, cap, named("subtext0"))

    def _bubble(self, s, y_cells):
        if not self.bubble:
            return
        text, until = self.bubble
        if self.t > until:
            self.bubble = None
            return
        gx = int(self.x) + MASCOT_W * max(1, self.k) // 2
        w = min(len(text) + 2, s.w - 2)
        x = max(1, min(s.w - w - 1, gx - w // 2))
        # one row of air above the head, so a hat has room
        y = max(0, y_cells - 3)
        s.text(x, y, " " + text[:w - 2] + " ", named("crust"), SC.named_bg("rosewater"))
        s.set(gx, y + 1, "▾", named("rosewater"))

    def step(self, s, dt):
        self.t += dt
        self.dt = dt
        self.caption_override = None
        if self.t > self.blink_at + 0.15:
            self.blink_at = self.t + random.uniform(2.0, 5.0)
        if self.glance and self.t > self.glance_at + 0.5:
            self.glance = 0; self.glance_at = self.t + random.uniform(2.5, 5.0)
        elif not self.glance and self.t > self.glance_at:
            self.glance = random.choice((-1, 1))
        self.k = self._scale(s)
        now = clock.now()
        if now["hour"] != getattr(self, "hour", now["hour"]):
            self.hour = now["hour"]
            self.fire("hour", **now)
            if now["hour"] == 0:
                self.fire("midnight", **now)
        self.hour = now["hour"]
        for fn in self.anim.ticks:
            self._safe(fn, "tick", self.ctx)
        if not self.k:
            self._bare(s)
            return
        self.u = 2 * self.k
        u = self.u
        fy = s.h - 4
        s.text(0, fy, "▀" * s.w, named("surface1"))
        sfy = fy * 2
        y = sfy - MASCOT_H * u
        q = Quad()
        for d in self.dust:
            d[2] += dt
            d[0] += (2.0 if d[0] > self.x * 2 + 8 * u else -2.0) * u * dt
            self._block(q, int(d[0]), int(d[1]), self._fade("surface2", max(0.1, 1.0 - d[2] / 0.5)))
        self.dust = [d for d in self.dust if d[2] < 0.5]
        if self.mode == "walk":
            self._walk(q, y)
        elif self.mode == "hop":
            self._hop(q, y)
        elif self.mode == "land":
            self._land(q, y)
        else:
            job = self.anim.idle_jobs.get(self.job)
            if job and job["draw"]:
                self._safe(job["draw"], "job " + str(self.job), self.ctx, q, int(self.x * 2), y, sfy)
            else:
                self._mascot(q, int(self.x * 2), y)
            self._caption(s, fy + 2)
            if self.t - self.t0 > self.dur:
                self._next(s)
        still = []
        self.ctx.q = q
        for name, gen in self.playing:
            try:
                next(gen)
                still.append((name, gen))
            except StopIteration:
                pass
            except Exception as e:  # noqa: BLE001
                self.anim.fail("reaction " + name, e)
        self.playing = still
        q.flush(s)
        self._bubble(s, y // 2)

    def _bare(self, s):
        self.k = 1
        self.u = 2
        q = Quad()
        x = max(0, (s.w - MASCOT_W) // 2)
        y = max(0, (s.h - MASCOT_H) // 2)
        job = self.anim.idle_jobs.get(self.job, {"eye": 0})
        self._mascot(q, x * 2, y * 2, self._look(job.get("eye", 0)), shut=self.job == "naps")
        q.flush(s)
        self._caption(s, y + MASCOT_H + 1)
        if self.t - self.t0 > self.dur:
            self._next(s)

    def _next(self, s):
        self.job = self._pick_job()
        self.dur = random.uniform(12.0, 16.0)
        self.target = float(self._spot(s))
        self.store = {}
        gap = abs(self.target - self.x)
        if gap < 30 * self.k and random.random() < 0.5:
            self.mode = "hop"; self.hop_x0 = self.x; self.hop_t0 = self.t
            self.hop_dur = 0.55 + gap / (40.0 * self.k)
        else:
            self.mode = "walk"; self.leg_i = 0; self.leg_t = 0.0
