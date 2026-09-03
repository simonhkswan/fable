"""A Borrowed Shadow. A layer behind Fable that lies on the floor.

By day it is a sundial: short at noon, long at dawn and dusk, always on the
side away from the sun. After sunset it lies to the west anyway, the wrong
colour, and breathes. In the small hours it now and then gets up.

On the hour it annotates the floor with the time, one glyph at a time, and
he glances down at it. At midnight it lets off sparks.
"""
import math
import random
from fable.mascot import BODY, NUBS, LEGS_STAND, face_row
from fable.screen import fg

S = {"stand_at": 25.0, "stand_t0": None, "note": None}
STAND_HOLD = 2.4
STAND_EVERY = (18.0, 40.0)
NIGHT_INK = "mauve"
DAY_INK = "crust"
LINES_DARK = ("it wrote that down already", "it keeps better time than i do",
              "that is not my hour", "i did not ask it to")
LINES_DAY = ("on the hour", "noted", "it is annotating again")


def _geometry(ctx, pose):
    """Where the shadow lies, in quarter cells. None when there is no floor."""
    s = ctx.screen
    if s is None or ctx.k == 0:
        return None
    u = pose["u"]
    floor = (s.h - 4) * 2
    feet = pose["y"] + 5 * u
    lift = max(0, floor - feet)
    c = ctx.clock
    if c["dark"]:
        way = 1
        length = 9 * u
        breath = 0.28 + 0.10 * math.sin(ctx.t * 0.9)
        rgb = ctx.fade(NIGHT_INK, breath * max(0.0, 1.0 - lift / (3.0 * u)))
    else:
        way = 1 if c["az"] > 0 else -1
        length = int(u * (3 + 13 * (1.0 - c["sun"])))
        rgb = ctx.fade(DAY_INK, (0.55 + 0.35 * c["sun"]) * max(0.0, 1.0 - lift / (3.0 * u)))
    length = int(length * max(0.3, 1.0 - lift / (4.0 * u)))
    x = pose["x"]
    body_l, body_r = x + 2 * u, x + 14 * u
    if way > 0:
        lo, hi, head = body_l + lift // 2, body_r + length, body_r + length - 3 * u
    else:
        lo, hi, head = body_l - length, body_r - lift // 2, body_l - length
    return {"floor": floor, "lo": lo, "hi": hi, "head": head, "way": way, "rgb": rgb,
            "u": u, "x": x, "y": pose["y"], "clock": c, "lift": lift}


def draw(ctx, q, pose):
    g = _geometry(ctx, pose)
    if g is None:
        return
    u, floor = g["u"], g["floor"]
    # the flat silhouette: the top half of the floor row, darker than the floor
    q.rect(g["lo"], floor, max(0, g["hi"] - g["lo"]), 1, g["rgb"])
    # the head, a lump at the far end that sits up one quarter
    q.rect(g["head"], floor - 1, 3 * u, 1, g["rgb"])
    if g["clock"]["phase"] == "small hours" and g["lift"] == 0:
        _stands(ctx, q, g)
    else:
        S["stand_t0"] = None


def _stands(ctx, q, g):
    """In the small hours the shadow gets up now and then and stands behind him."""
    t = ctx.t
    if S["stand_t0"] is None:
        if t < S["stand_at"]:
            return
        S["stand_t0"] = t
        S["stand_at"] = t + STAND_HOLD + random.uniform(*STAND_EVERY)
    held = t - S["stand_t0"]
    if held > STAND_HOLD:
        S["stand_t0"] = None
        return
    u = g["u"]
    f = min(1.0, held / 0.25)                 # it rises in a quarter second, then holds
    rise = int(f * 5 * u)
    ink = ctx.fade(NIGHT_INK, 0.22)
    sx = g["x"] + g["way"] * 10 * u
    rows = (BODY, face_row(0), NUBS, BODY, LEGS_STAND)[-max(1, rise // u):]
    top = g["floor"] - len(rows) * u
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch != ".":
                q.rect(sx + gx * u, top + gy * u, u, u, ink)
    # he notices. the glance is held toward it while it stands.
    ctx.guy.glance = g["way"]
    ctx.guy.glance_at = t


def on_hour(ctx, data):
    """The shadow writes the hour on the floor, one glyph every quarter second."""
    text = data.get("text") or ctx.clock["text"]
    dark = data.get("dark", ctx.clock["dark"])
    ink = NIGHT_INK if dark else "overlay1"
    t0 = ctx.t
    shown = 0.0
    while True:
        held = ctx.t - t0
        if held > 7.5:
            break
        pose = ctx.guy.last_pose
        if not pose:
            yield
            continue
        g = _geometry(ctx, pose)
        if g is None:
            yield
            continue
        n = min(len(text), int(held / 0.25) + 1)
        f = 1.0 if held < 5.5 else max(0.0, 1.0 - (held - 5.5) / 2.0)
        col = g["head"] // 2 + (3 * g["u"] // 2 + 1 if g["way"] > 0 else -len(text) - 1)
        col = max(0, min(ctx.screen.w - len(text), col))
        ctx.screen.text(col, ctx.screen.h - 4, text[:n], fg(*ctx.fade(ink, f)))
        if held < 2.0:
            ctx.guy.glance = g["way"]
            ctx.guy.glance_at = ctx.t
        yield
    if random.random() < (0.5 if dark else 0.2):
        ctx.guy.say(random.choice(LINES_DARK if dark else LINES_DAY), 3.5)


def on_midnight(ctx, data):
    """Sparks from the shadow's head, the wrong colour."""
    ctx.guy.say("midnight. it is still there.", 4.0)
    t0 = ctx.t
    next_burst = t0
    while ctx.t - t0 < 2.0:
        pose = ctx.guy.last_pose
        g = _geometry(ctx, pose) if pose else None
        if g and ctx.t >= next_burst:
            next_burst = ctx.t + 0.3
            ctx.burst(g["head"] + g["u"], g["floor"] - 2, 4, (NIGHT_INK, "lavender", "surface2"))
        ctx.sparks(ctx.q)
        yield
    while ctx.guy.sparks:
        ctx.sparks(ctx.q)
        yield


def register(anim, world):
    anim.layer("borrowed_shadow", z=-2, draw=draw)
    anim.reaction("hour", on_hour)
    anim.reaction("midnight", on_midnight)
