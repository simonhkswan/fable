"""A Prior-Art Figure. Press p.

He reaches behind his back and hauls a framed figure up over his head. He
holds it there, because a thing held is a thing that matters. Then he drops
it into the document beside him. It lands with dust and a number, stands on
the floor for a while, and fades the way references do.

Every figure is numbered. The count lives next to this file and survives a
restart, so FIG. 1 stays FIG. 1. The sketches come from PatentCopilot#20747,
which let the AI insert a prior-art figure into an Editor V2 document.

How it is drawn: a layer behind the body carries the reach and the hold, so
the figure comes up from behind his back. A reaction carries the drop and the
exhibit, in front. A tick holds the caption while any of it plays.
"""
import json
import os
import random

from fable.screen import fg

HERE = os.path.dirname(os.path.abspath(__file__))
COUNT_FILE = os.path.join(HERE, "figures.json")
KEY = "p"
COOLDOWN = 4.5
REACH, HOLD, DROP, SHOW, FADE = 0.35, 0.6, 0.18, 4.5, 1.4

# 9 wide, 6 tall, in sprite pixels. # frame, . nothing, letters are ink names below.
FRAME_INK = {"#": "overlay1", "i": "text", "d": "subtext0", "b": "yellow", "m": "maroon"}
SKETCHES = {
    "a wheel":   ("#########", "#..iii..#", "#.i.i.i.#", "#.iiiii.#", "#..iii..#", "#########"),
    "a lever":   ("#########", "#i......#", "#.ii....#", "#...iii.#", "#..d.d..#", "#########"),
    "a bulb":    ("#########", "#..bbb..#", "#.bbbbb.#", "#..bbb..#", "#..did..#", "#########"),
    "a gear":    ("#########", "#.i.i.i.#", "#..iii..#", "#.ii.ii.#", "#..iii..#", "#########"),
    "a mug":     ("#########", "#.iiii..#", "#.immii.#", "#.immii.#", "#.iiii..#", "#########"),
    "a hinge":   ("#########", "#.ii.ii.#", "#.iidii.#", "#.ii.ii.#", "#.ii.ii.#", "#########"),
    "a spring":  ("#########", "#.i.....#", "#..i.i..#", "#...i...#", "#..i.i..#", "#########"),
}
FIG_W, FIG_H = 9, 6
LINES = ("prior art!", "into the document it goes", "somebody thought of it first",
         "inserted. heroically.", "figure, meet claim", "ENG-10718: fixed")
BUSY = ("one figure at a time", "the editor is still open", "let it land")

# the one figure in flight: t0, rows, number, caption. None between casts.
S = {"next_at": 0.0, "live": None}


def _count():
    try:
        with open(COUNT_FILE) as f:
            return int(json.load(f).get("figures", 0))
    except (OSError, ValueError):
        return 0


def _bump():
    n = _count() + 1
    try:
        with open(COUNT_FILE, "w") as f:
            json.dump({"figures": n}, f)
    except OSError:
        pass
    return n


def _figure(ctx, q, x, y, rows, f=1.0):
    """Draw one figure with its top-left corner at (x, y) in quarter cells."""
    u = ctx.u
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            if ch == ".":
                continue
            ink = FRAME_INK.get(ch, "overlay1")
            if f >= 1.0:
                ctx.cell(q, x + gx * u, y + gy * u, ink)
            else:
                ctx.block(q, x + gx * u, y + gy * u, ctx.fade(ink, f))


def _spots(ctx, pose):
    """Where it starts, where he holds it, where it lands. Quarter cells."""
    u = ctx.u
    s = ctx.screen
    gx, gy = pose["x"], pose["y"]
    floor = (s.h - 4) * 2
    start = (gx + 3 * u, floor - 2 * u)
    hold = (gx + 3 * u, gy - (FIG_H + 1) * u)
    # his props (the laptop, the mug, the book) sit on his right. It lands on his left.
    land_x = gx - (FIG_W + 2) * u
    if land_x < 0:
        land_x = gx + 28 * u
    if land_x + FIG_W * u > s.w * 2:
        land_x = max(0, s.w * 2 - FIG_W * u)
    land = (land_x, floor - FIG_H * u)
    return start, hold, land


def cast(ctx):
    if ctx.k == 0:
        ctx.guy.say("no room for a figure here", 2.5)
        return
    if ctx.t < S["next_at"]:
        ctx.guy.say(random.choice(BUSY), 2.0)
        return
    S["next_at"] = ctx.t + COOLDOWN
    ctx.guy.fire("figure", number=_bump(), sketch=random.choice(list(SKETCHES)))


def behind(ctx, q, pose):
    """The layer. Draws the reach and the hold behind his body."""
    live = S["live"]
    if live is None or ctx.screen is None:
        return
    held = ctx.t - live["t0"]
    if held >= REACH + HOLD:
        return
    start, hold, _ = _spots(ctx, pose)
    if held < REACH:
        f = held / REACH
        f = f * f                       # it comes up slow, then fast
        _figure(ctx, q, start[0], int(start[1] + (hold[1] - start[1]) * f), live["rows"])
    else:
        _figure(ctx, q, hold[0], hold[1], live["rows"])


def hold_caption(ctx):
    """The tick. The mascot clears the caption each frame before the jobs draw,
    so the figure's caption is put back here, ahead of them."""
    live = S["live"]
    if live is not None and live.get("caption"):
        ctx.caption(live["caption"])


def play(ctx, data):
    """The reaction. Owns the timing, the eyes, the drop and the exhibit."""
    n = data.get("number", 1)
    rows = SKETCHES.get(data.get("sketch"), SKETCHES["a wheel"])
    label = "FIG. %d" % n
    live = S["live"] = {"t0": ctx.t, "rows": rows, "caption": "reaching for prior art"}
    dusted = said = False
    try:
        while True:
            held = ctx.t - live["t0"]
            pose = ctx.guy.last_pose
            s = ctx.screen
            if not pose or s is None or ctx.k == 0:
                yield
                continue
            u = ctx.u
            gx = pose["x"]
            floor = (s.h - 4) * 2
            _, hold, land = _spots(ctx, pose)
            way = 1 if land[0] > gx else -1
            if held < REACH:
                live["caption"] = "reaching for prior art"
                ctx.guy.glance = 0
                ctx.guy.glance_at = ctx.t
            elif held < REACH + HOLD:
                live["caption"] = "prior art!"
                ctx.guy.glance = 0
                ctx.guy.glance_at = ctx.t
            elif held < REACH + HOLD + DROP:
                f = (held - REACH - HOLD) / DROP
                live["caption"] = "inserting"
                _figure(ctx, ctx.q, int(hold[0] + (land[0] - hold[0]) * f),
                        int(hold[1] + (land[1] - hold[1]) * f * f), rows)
                ctx.guy.glance = way
                ctx.guy.glance_at = ctx.t
            elif held < REACH + HOLD + DROP + SHOW + FADE:
                since = held - REACH - HOLD - DROP
                if not dusted:
                    dusted = True
                    for _ in range(6):
                        ctx.guy.dust.append([float(land[0] + random.randint(0, FIG_W * u)), float(floor - 1), 0.0])
                    ctx.burst(land[0] + FIG_W * u // 2, land[1], 5, ("yellow", "peach", "text"))
                f = 1.0 if since < SHOW else max(0.0, 1.0 - (since - SHOW) / FADE)
                live["caption"] = "inserted" if since < 1.5 else None
                _figure(ctx, ctx.q, land[0], land[1], rows, f)
                col = land[0] // 2 + (FIG_W * u // 2 - len(label)) // 2
                col = max(0, min(s.w - len(label), col))
                s.text(col, s.h - 4, label, fg(*ctx.fade("subtext0", f)))
                ctx.sparks(ctx.q)
                if since < 1.2:
                    ctx.guy.glance = way
                    ctx.guy.glance_at = ctx.t
                if not said and since > 0.3:
                    said = True
                    ctx.guy.say("FIG. 1. a wheel. of course." if n == 1 else random.choice(LINES), 3.5)
            else:
                break
            yield
        while ctx.guy.sparks:
            ctx.sparks(ctx.q)
            yield
    finally:
        S["live"] = None


def register(anim, world):
    anim.layer("prior_art_figure", z=-1, draw=behind)
    anim.tick(hold_caption)
    anim.reaction("figure", play)
    anim.key(KEY, cast, help="figure")
