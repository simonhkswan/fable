"""Rename Tag. A three-pixel sticker on the guy's chest. Every few seconds it
peels, flips, and comes back as a different name. Dropped by a PR that renamed
a whole project, so the tag never settles either.

Drawn as a layer, so it follows every pose: walk, hop, land, squash, and the
bare sprite when the pane is too small for anything else."""
import random

# Names the tag can carry, by the colour of the file it would be written in.
NAMES = [
    ("insight", "sky"),
    ("the guy", "clay"),
    ("main.py", "yellow"),
    ("conf.yaml", "red"),
    ("README.md", "lavender"),
    ("v2 (final)", "peach"),
    ("untitled", "overlay1"),
    ("new name", "green"),
]
COLS = (6, 7, 8)      # sprite columns, centred on the chest row
ROW = 3               # the body row under the nubs, same y in squash or not
PEEL = 0.24           # seconds the old tag lifts before the new one lands
FLASH = 0.10          # seconds the new tag shows white

S = {"i": 0, "next": 0.0, "peel_at": None, "said": False}


def _pick():
    j = random.randrange(len(NAMES))
    if j == S["i"]:
        j = (j + 1) % len(NAMES)
    S["i"] = j


def draw_tag(ctx, q, pose):
    u = pose["u"]
    x, y = pose["x"], pose["y"] + ROW * u
    t = ctx.t
    if S["next"] == 0.0:
        S["next"] = t + random.uniform(5.0, 9.0)
    name, ink = NAMES[S["i"]]
    if S["peel_at"] is None and t >= S["next"]:
        S["peel_at"] = t
    if S["peel_at"] is not None:
        age = t - S["peel_at"]
        if age < PEEL:
            # the old tag lifts and fades, corner first
            f = 1.0 - age / PEEL
            lift = int(u * (1.0 - f) * 1.5)
            for n, c in enumerate(COLS):
                ctx.block(q, x + c * u, y - lift * (n + 1) // 3, ctx.fade(ink, max(0.2, f)))
            return
        if age < PEEL + FLASH:
            if not S["said"]:
                _pick()
                S["said"] = True
                if ctx.k >= 2 and random.random() < 0.35:
                    ctx.guy.say("call me %s" % NAMES[S["i"]][0], 2.5)
            for c in COLS:
                ctx.cell(q, x + c * u, y, "text")
            return
        S["peel_at"] = None
        S["said"] = False
        S["next"] = t + random.uniform(5.0, 9.0)
        name, ink = NAMES[S["i"]]
    for c in COLS:
        ctx.cell(q, x + c * u, y, ink)


def on_equip(ctx, data):
    if data.get("item") not in (None, "49cb13e8"):
        return
    ctx.guy.say("new name. same guy.", 3.0)


def register(anim, world):
    anim.layer("rename_tag", z=1, draw=draw_tag)
    anim.reaction("equip", on_equip)
