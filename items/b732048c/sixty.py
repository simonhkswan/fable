"""max-width: 60%. The guy is reflowed to sixty percent of his width, under a
thin header bar with a logo. Everything he says is clipped at sixty percent
too, and ends in an ellipsis. That is the curse.

Three shapes: 100%, 80%, 60%. Equipping steps through them with held frames,
like a responsive layout hitting its breakpoints, and lands with a squash.
Shape 60% is where he stays. Unequip rebuilds the guy, so nothing to undo.
"""
import math
from termguy import mascot as M
from termguy import screen as SC

ID = "b732048c"
RATIO = 0.6
BAR_INK = "overlay0"
LOGO_INK = "mauve"

# Each shape is a full 16-column row set so x positions stay where the layers expect them.
SHAPES = (
    # 100%: the guy as he was
    {"nubs": M.NUBS, "body": M.BODY, "eyes": (M.EYE_L, M.EYE_R),
     "stand": M.LEGS_STAND, "stride": M.LEGS_STRIDE, "tuck": M.LEGS_TUCK, "bar": (2, 12)},
    # 80%: mid-breakpoint, held for a moment
    {"nubs": ".#############..", "body": "...##########...", "eyes": (5, 10),
     "stand": "....#.#..#.#....", "stride": "...#..#..#..#...", "tuck": ".....##..##.....", "bar": (2, 10)},
    # 60%: max-width reached. The eyes get very close together.
    {"nubs": "...##########...", "body": "....########....", "eyes": (6, 9),
     "stand": "....#.#..#.#....", "stride": "...#..#..#..#...", "tuck": ".....##..##.....", "bar": (3, 10)},
)
HOLD = (0.14, 0.18)     # how long the 100% and 80% shapes are held on the way down
LAND = 0.16             # the squash when 60% is reached


def clip(text):
    """text-overflow: ellipsis, at sixty percent of the width."""
    if not text or len(text) <= 3:
        return text
    keep = max(1, math.ceil(len(text) * RATIO) - 1)
    return text[:keep] + "…"


def face_row(shape, e):
    row = list(shape["body"])
    l, r = shape["eyes"]
    row[l + e] = "."
    row[r + e] = "."
    return "".join(row)


def legs_for(shape, legs):
    if legs == M.LEGS_STRIDE:
        return shape["stride"]
    if legs == M.LEGS_TUCK:
        return shape["tuck"]
    return shape["stand"]


def install(guy):
    """Wrap the guy's own drawing and speech once. reload() builds a fresh Guy, so
    unequipping leaves no trace."""
    if getattr(guy, "_sixty", None) is not None:
        return
    guy._sixty = {"shape": 2, "squash": 0.0}
    orig_say = guy.say

    def mascot(q, x, y, eye=0, lean=0, legs=M.LEGS_STAND, squash=False, shut=False):
        st = guy._sixty
        shape = SHAPES[st["shape"]]
        u = guy.u
        squash = squash or st["squash"] > guy.t
        if shut or guy.blink_at < guy.t < guy.blink_at + 0.15:
            face = shape["body"]
        else:
            face = face_row(shape, eye)
        tilt = lean * (u // 2)
        pose = {"x": x, "y": y, "eye": eye, "lean": lean, "squash": squash, "shut": shut, "u": u}
        for z, name, draw in guy.anim.layers:
            if z < 0 and draw:
                guy._safe(draw, "layer " + name, guy.ctx, q, pose)
        rows = (shape["nubs"], shape["body"], legs_for(shape, legs))
        if squash:
            guy._grid(q, x + tilt, y + u, (face,))
            guy._grid(q, x, y + 2 * u, rows)
        else:
            guy._grid(q, x + tilt, y, (shape["body"], face))
            guy._grid(q, x, y + 2 * u, rows)
        # the header: a thin bar one pixel above the head, with a small logo at the left.
        # It does not tilt with the head. Headers never do.
        bx, bw = shape["bar"]
        by = y - 2 * u + (u if squash else 0)
        for i in range(bw):
            guy._cell(q, x + (bx + i) * u, by, LOGO_INK if i < 2 else BAR_INK)
        for z, name, draw in guy.anim.layers:
            if z >= 0 and draw:
                guy._safe(draw, "layer " + name, guy.ctx, q, pose)
        guy.last_pose = pose

    def say(text, seconds=4.0):
        orig_say(clip(text), seconds)

    def caption(s, y):
        cap = guy.caption_override
        if cap is None and guy.job in guy.anim.idle_jobs:
            cap = guy.anim.idle_jobs[guy.job]["caption"]
        cap = clip(cap)
        if cap and y <= s.h - 2 and len(cap) < s.w:
            s.text((s.w - len(cap)) // 2, y, cap, SC.named("subtext0"))

    guy._mascot = mascot
    guy.say = say
    guy._caption = caption


def tick(ctx):
    install(ctx.guy)


def reflow(ctx, data):
    """Equipped: step down through the breakpoints, hold each, squash on arrival."""
    if data.get("item") not in (None, ID):
        return None
    guy = ctx.guy
    install(guy)
    st = guy._sixty

    def play():
        for i, hold in enumerate(HOLD):
            st["shape"] = i
            t0 = guy.t
            while guy.t - t0 < hold:
                yield
        st["shape"] = 2
        st["squash"] = guy.t + LAND
        while guy.t < st["squash"]:
            yield
        guy.say("max-width reached", 3.0)
    return play()


def register(anim, world):
    anim.tick(tick)
    anim.reaction("equip", reflow)
