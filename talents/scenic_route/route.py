"""Scenic Route. Press g and the guy takes the long way round his own pane:
out to one edge, back to the other, then home. He walks at a stroll, not his
usual clip, and he stops for everything that glints on the floor. The whole
trip takes a minute at the very least. That is the constraint, and also the
point. He comes back with his pockets full and says so.

Built as an idle job with weight 0, so the guy never wanders off on his own.
The key press puts him in the job, and the job steers him along the route."""
import random

JOB = "scenic_route"
STROLL = (2.0, 5.0)          # cells per second, min and max. His walk is 16.
STEP_HOLD = (0.30, 0.42)     # seconds per leg frame. Twice as slow as his walk.
AIM = 72.0                   # seconds the whole trip aims for
FLOOR = 62.0                 # the constraint: never shorter than this
PICK = 3.6                   # seconds spent on one souvenir
GAWK = 2.5                   # seconds spent at an edge, looking off the pane
COOLDOWN = 20.0              # seconds before he will go again

LEGS_STAND = "...#.#....#.#..."
LEGS_STRIDE = "..#...#..#...#.."

# What he finds. Name, ink, and how wide it lies on the floor.
SOUVENIRS = [
    ("a coin", "yellow", 1),
    ("someone's pen", "sky", 2),
    ("a pebble with a face", "overlay2", 1),
    ("a bottle cap", "peach", 1),
    ("a paperclip", "subtext0", 2),
    ("half a ticket", "rosewater", 2),
    ("a key to nothing", "flamingo", 2),
    ("a shiny bolt", "teal", 1),
    ("a button, not his", "mauve", 1),
    ("a very good stick", "clay", 3),
    ("a marble", "green", 1),
    ("a receipt for 0.00", "text", 2),
]
GREED = ("ooh.", "mine.", "nobody wants this.", "finders keepers.", "for later.", "that is coming with me.")

S = {"last_end": -1e9, "world": None}


def _reset_pose(guy, legs=LEGS_STAND):
    guy.leg_i = 0
    guy.leg_t = 0.0


def start(ctx):
    guy = ctx.guy
    if guy.job == JOB and guy.store.get("route"):
        guy.say("already on it. Slowly.", 3.0)
        return
    if not guy.k or guy.screen is None:
        guy.say("no room to wander.", 3.0)
        return
    if guy.t - S["last_end"] < COOLDOWN:
        guy.say("let me put these away first.", 3.0)
        return
    s, k = guy.screen, guy.k
    lo, hi = 1.0 * k, float(s.w - 17 * k)
    if hi - lo < 20 * k:
        guy.say("no room to wander.", 3.0)
        return
    home = float(guy.x)
    # Souvenirs lie across the whole pane. None too close to another.
    n = random.randint(5, 7)
    xs = []
    tries = 0
    while len(xs) < n and tries < 200:
        tries += 1
        sx = random.uniform(lo + 2 * k, hi + 14 * k)
        if all(abs(sx - o) > 6 * k for o in xs) and abs(sx - (home + 8 * k)) > 6 * k:
            xs.append(sx)
    finds = random.sample(SOUVENIRS, len(xs))
    sights = [{"x": sx, "name": f[0], "ink": f[1], "w": f[2], "got": False} for sx, f in zip(xs, finds)]
    # The route: right to the edge, left to the other edge, then home. He stands
    # 8 cells left of a thing to be over it, so a stop at a sight is at x - 8k.
    right_way = sorted([g for g in sights if g["x"] - 8 * k > home], key=lambda g: g["x"])
    left_way = sorted([g for g in sights if g["x"] - 8 * k <= home], key=lambda g: -g["x"])
    stops = [{"x": min(hi, max(lo, g["x"] - 8 * k)), "sight": g, "hold": PICK} for g in right_way]
    stops.append({"x": hi, "sight": None, "hold": GAWK, "edge": 1})
    stops += [{"x": min(hi, max(lo, g["x"] - 8 * k)), "sight": g, "hold": PICK} for g in left_way]
    stops.append({"x": lo, "sight": None, "hold": GAWK, "edge": -1})
    stops.append({"x": home, "sight": None, "hold": 0.0, "home": True})
    dist, px = 0.0, home
    for st in stops:
        dist += abs(st["x"] - px)
        px = st["x"]
    holds = sum(st["hold"] for st in stops)
    speed = dist / max(1.0, AIM - holds)
    speed = max(STROLL[0], min(STROLL[1], speed))
    total = dist / speed + holds
    if total < FLOOR:
        # Not enough pane for a minute at a stroll. He lingers longer over each thing.
        extra = (FLOOR - total) / max(1, len(stops) - 1)
        for st in stops:
            if not st.get("home"):
                st["hold"] += extra
        total = FLOOR
    guy.job = JOB
    guy.mode = "do"
    guy.t0 = guy.t
    guy.dur = total + 4.0
    guy.target = guy.x
    guy.store = {"route": True, "stops": stops, "sights": sights, "i": 0, "speed": speed,
                 "hold_t0": None, "got": 0, "total": total, "way": 1, "done": False, "said": False}
    _reset_pose(guy)
    guy.say("back in a minute. Maybe two.", 3.5)


def _draw_sights(ctx, q, st, fy):
    u, k, t = ctx.u, ctx.k, ctx.t
    for g in st["sights"]:
        if g["got"]:
            continue
        gx = int(g["x"] * 2)
        gy = fy - u
        glint = int((t * 2.0 + g["x"]) % 7) == 0
        for i in range(g["w"]):
            ctx.cell(q, gx + i * u, gy, "text" if glint else g["ink"])


def _finish(ctx, st):
    guy = ctx.guy
    st["done"] = True
    S["last_end"] = guy.t
    got = st["got"]
    if got == 0:
        guy.say("nothing. Pockets still full though.", 4.0)
    else:
        guy.say("back. pockets full. %d thing%s." % (got, "" if got == 1 else "s"), 5.0)
    state = ctx.state
    c = state.setdefault("counters", {})
    c["souvenirs"] = c.get("souvenirs", 0) + got
    w = S["world"]
    if w is not None:
        try:
            w.remember("took the scenic route, pocketed %d thing%s" % (got, "" if got == 1 else "s"), "item")
            w.save()
        except Exception:  # noqa: BLE001
            pass
    ctx.burst(int(guy.x * 2) + 8 * ctx.u, guy.last_pose.get("y", 0) - ctx.u, 8,
              ("yellow", "peach", "sky", "teal", "mauve"))
    guy.dur = (guy.t - guy.t0) + 2.5


def draw(ctx, q, x, y, fy):
    guy, st, u, k = ctx.guy, ctx.store, ctx.u, ctx.k
    if not st.get("route"):
        ctx.mascot(q, x, y, eye=ctx.look(1))
        return
    if st["done"]:
        ctx.sparks(q)
        ctx.mascot(q, int(guy.x * 2), y, eye=ctx.look(0))
        ctx.caption("home. counting")
        return
    elapsed = guy.t - guy.t0
    guy.dur = max(guy.dur, elapsed + 5.0)         # the route ends the trip, not the clock
    _draw_sights(ctx, q, st, fy)
    stop = st["stops"][st["i"]]
    left = max(0, int(st["total"] - elapsed))
    ctx.caption("the scenic route · %d pocketed · %ds to go" % (st["got"], left))
    gx = int(guy.x * 2)
    if st["hold_t0"] is None:
        # strolling toward the next stop
        gap = stop["x"] - guy.x
        way = 1 if gap > 0 else -1
        step = st["speed"] * ctx.dt
        if abs(gap) <= step:
            guy.x = stop["x"]
            st["hold_t0"] = guy.t
            _reset_pose(guy)
        else:
            guy.x += way * step
            st["way"] = way
        guy.leg_t += ctx.dt
        if guy.leg_t > STEP_HOLD[guy.leg_i]:
            guy.leg_t = 0.0
            guy.leg_i ^= 1
        legs = LEGS_STRIDE if guy.leg_i else LEGS_STAND
        ctx.sparks(q)
        ctx.mascot(q, int(guy.x * 2), y, eye=st["way"], lean=st["way"], legs=legs)
        return
    held = guy.t - st["hold_t0"]
    g = stop.get("sight")
    if g is not None and not g["got"]:
        # bend, grab, straighten, gloat
        if held < PICK * 0.45:
            ctx.mascot(q, gx, y, eye=0, squash=True, shut=held > PICK * 0.3)
        else:
            g["got"] = True
            st["got"] += 1
            ctx.burst(int(g["x"] * 2) + u, fy - u, 6, (g["ink"], "yellow", "text"))
            guy.say("%s %s" % (random.choice(GREED), g["name"]), min(2.8, PICK - held))
            ctx.mascot(q, gx, y, eye=0)
    elif stop.get("edge"):
        # a long look off the edge of the pane, then the other way
        e = stop["edge"] if held < stop["hold"] * 0.6 else -stop["edge"]
        ctx.mascot(q, gx, y, eye=e, lean=e if held < stop["hold"] * 0.6 else 0)
    else:
        ctx.sparks(q)
        ctx.mascot(q, gx, y, eye=ctx.look(0))
    if stop.get("home") or held >= stop["hold"]:
        if stop.get("home"):
            _finish(ctx, st)
            return
        st["i"] += 1
        st["hold_t0"] = None
        if st["i"] >= len(st["stops"]):
            _finish(ctx, st)


def register(anim, world):
    S["world"] = world
    anim.idle_job(JOB, weight=0, caption="taking the scenic route", draw=draw, eye=1)
    anim.key("g", start, help="scenic route (slow, a minute or more)")
