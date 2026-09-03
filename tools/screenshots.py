#!/usr/bin/env python3
"""Render README screenshots through the real widget pages, with made-up
content. Run from the repo root:

    uv run --with pillow tools/screenshots.py

It copies the repo to a scratch directory, plants mock state, items, talents and
queue entries there, renders each page headless, and writes PNGs to
docs/screenshots/. Nothing in the real repo changes except those PNGs.
"""
import json
import os
import random
import shutil
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

REAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REAL, "docs", "screenshots")
COLS, ROWS = 100, 30
CW, CH = 10, 20          # pixels per cell
FONT_SIZE = 15


# ── a scratch copy of the game ────────────────────────────────────────────
def make_copy():
    tmp = tempfile.mkdtemp(prefix="fable-shots-")
    root = os.path.join(tmp, "fable")
    shutil.copytree(REAL, root, ignore=shutil.ignore_patterns(".git", "runs", "__pycache__", "items", "queue",
                                                              "docs", "state.json", "*.jsonl", "presence.json"))
    for d in ("items", "queue", "runs"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    return root


def load_game(root):
    for name in [m for m in sys.modules if m == "fable" or m.startswith("fable.")]:
        del sys.modules[name]
    sys.path.insert(0, root)
    import fable.paths as paths  # noqa
    assert paths.ROOT == root, paths.ROOT
    from fable import ui, state, screen
    return ui, state, screen


def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        if isinstance(obj, str):
            f.write(obj)
        else:
            json.dump(obj, f, indent=2)


# ── glyphs to pixels ──────────────────────────────────────────────────────
QUAD = (" ", "▗", "▖", "▄", "▝", "▐", "▞", "▟", "▘", "▚", "▌", "▙", "▀", "▜", "▛", "█")
MASK = {ch: i for i, ch in enumerate(QUAD)}   # bit 8 TL, 4 TR, 2 BL, 1 BR


def sgr_rgb(s, default):
    if not s:
        return default
    parts = s.strip("\x1b[m").split(";")
    try:
        if parts[0] in ("38", "48") and parts[1] == "2":
            return tuple(int(p) for p in parts[2:5])
    except (IndexError, ValueError):
        pass
    return default


def font():
    for path in ("/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/SFNSMono.ttf",
                 os.path.expanduser("~/Library/Fonts/Hurmit Medium Nerd Font Complete.otf")):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, FONT_SIZE)
            except OSError:
                continue
    return ImageFont.load_default()


def render(screen, palette, path):
    base = palette["base"]
    text = palette["text"]
    img = Image.new("RGB", (COLS * CW + 2 * CW, ROWS * CH + 2 * CH), base)
    d = ImageDraw.Draw(img)
    f = font()
    for y in range(screen.h):
        for x in range(screen.w):
            ch, fg, bg = screen.cells[y * screen.w + x]
            px, py = (x + 1) * CW, (y + 1) * CH
            bgc = sgr_rgb(bg, base)
            fgc = sgr_rgb(fg, text)
            if bg:
                d.rectangle([px, py, px + CW - 1, py + CH - 1], fill=bgc)
            if ch == " " or ch is None:
                continue
            if ch in MASK:
                m = MASK[ch]
                hw, hh = CW // 2, CH // 2
                for bit, (ox, oy) in ((8, (0, 0)), (4, (hw, 0)), (2, (0, hh)), (1, (hw, hh))):
                    if m & bit:
                        d.rectangle([px + ox, py + oy, px + ox + hw - 1, py + oy + hh - 1], fill=fgc)
                continue
            if ch == "░":
                blend = tuple(int(b + (a - b) * 0.35) for a, b in zip(fgc, bgc))
                d.rectangle([px, py, px + CW - 1, py + CH - 1], fill=blend)
                continue
            if ch == "▏":
                d.rectangle([px, py, px + 1, py + CH - 1], fill=fgc)
                continue
            d.text((px, py + 1), ch, font=f, fill=fgc)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    print("wrote", os.path.relpath(path, REAL))


# ── the mocks ─────────────────────────────────────────────────────────────
MOCK_QUEUE = [
    ("item", "rare", "item", "ability", "reward for level 5"),
    ("item", "common", "item", "cosmetic", "dropped by merged wisp#38"),
    ("item", "epic", "extend", "travel", "dropped by reviewed PatentCopilot#20233"),
    ("category", "common", "item", "__new__", "milestone at level 10"),
    ("item", "legendary", "mutate", "possession", "reward for level 15"),
    ("talents", "rare", "item", "travel", "branches from Wanderlust"),
]

MOCK_TALENTS = [
    # id, name, kind, parent, pos, hint
    ("root", "Fable", "passive", None, [0, 0], "Where it starts."),
    ("deep_thought", "Deep Thought", "skill", "root", [0, -1], "He can stop and think about it."),
    ("long_stare", "Long Stare", "passive", "deep_thought", [0, -2], "+1 focus."),
    ("second_look", "Second Look", "passive", "long_stare", [-1, -3], "Reviews feed focus twice as often."),
    ("owl_hours", "Owl Hours", "skill", "long_stare", [1, -3], "After midnight his eyes glow and he reads faster."),
    ("steady_hands", "Steady Hands", "passive", "root", [-2, -1], "+1 craft."),
    ("tidy_desk", "Tidy Desk", "passive", "steady_hands", [-3, -2], "Cosmetic items cost one level less."),
    ("solder", "Solder", "skill", "steady_hands", [-4, -1], "He can fix a broken item once a day."),
    ("deep_pockets", "Deep Pockets", "passive", "root", [2, -1], "One more slot."),
    ("deeper_pockets", "Deeper Pockets", "passive", "deep_pockets", [3, -2], "One more slot."),
    ("hoarder", "Hoarder", "passive", "deeper_pockets", [4, -3], "Drops roll twice. Keep the better."),
    ("lucky_penny", "Lucky Penny", "passive", "root", [-2, 1], "+1 luck."),
    ("black_cat", "Black Cat", "skill", "lucky_penny", [-3, 2], "A cat. It walks across the pane at odd hours."),
    ("ladder", "Under the Ladder", "passive", "lucky_penny", [-4, 1], "Cursed items are 2 levels cheaper."),
    ("wanderlust", "Wanderlust", "passive", "root", [2, 1], "Travel items get +4 budget."),
    ("scenic_route", "Scenic Route", "skill", "wanderlust", [3, 2], "He takes the long way. Floating pane, slow glide."),
    ("frequent_flyer", "Frequent Flyer", "passive", "wanderlust", [4, 1], "Travel items drop twice as often."),
    ("passport", "Passport", "passive", "scenic_route", [3, 3], "He can visit other tabs."),
    ("stowaway", "Stowaway", "skill", "passport", [4, 4], "He hides in a pane you open and pops out later."),
    ("small_talk", "Small Talk", "passive", "root", [0, 2], "+1 charm."),
    ("gossip", "Gossip", "skill", "small_talk", [-1, 3], "He repeats things he read in your PR titles."),
    ("orator", "Orator", "passive", "small_talk", [1, 3], "Speech bubbles hold twice as long."),
    ("ghostwriter", "Ghostwriter", "skill", "orator", [1, 4], "He drafts your PR description while you type."),
]
MOCK_OWNED = ["root", "deep_thought", "long_stare", "steady_hands", "deep_pockets", "wanderlust", "scenic_route",
              "small_talk", "lucky_penny"]

CROWN = '''"""Crown of Closed Tabs. A legendary hat: every tab he ever closed, remembered as a point."""
import math


def draw(ctx, q, pose):
    u = pose["u"]
    x, y = pose["x"], pose["y"]
    rows = ("#.#.#.#.#.#.#.#.", "################")
    ink = {"#": "mauve"}
    # the points glint one at a time
    lit = int(ctx.t * 6) % 8
    top = list(rows[0])
    top[lit * 2] = "L"
    ctx.grid(q, x, y - 2 * u, ("".join(top), rows[1]), {"#": "mauve", "L": "rosewater"})


def register(anim, world):
    anim.layer("crown", z=1, draw=draw)
'''

HALO = '''"""Static Halo. A ring of dead pixels that orbits him, behind the body."""
import math


def draw(ctx, q, pose):
    u = pose["u"]
    cx = pose["x"] + 8 * u
    cy = pose["y"] + 2 * u
    for i in range(14):
        a = ctx.t * 1.6 + i * (2 * math.pi / 14)
        px = int(cx + math.cos(a) * 13 * u)
        py = int(cy + math.sin(a) * 5 * u)
        f = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(a * 2 + ctx.t * 3))
        ctx.block(q, px, py, ctx.fade("sky" if i % 3 else "lavender", f))


def register(anim, world):
    anim.layer("halo", z=-1, draw=draw)
'''

FAMILIAR = '''"""The Familiar. Something that came out of a possessed pane and did not go back."""
import math

GHOST = ("..####..", ".######.", "##.##.##", "########", "#.#..#.#")


def confer(ctx, q, x, y, fy):
    u = ctx.u
    bob = int(math.sin(ctx.t * 2.0) * u)
    gx, gy = x + 20 * u, y + u + bob
    ctx.grid(q, gx, gy, GHOST, {"#": "teal"})
    # it whispers: little marks between them
    for i in range(3):
        if int(ctx.t * 4 + i) % 3 == 0:
            ctx.cell(q, x + 17 * u + i * u, y - u - i * (u // 2), "surface2")
    ctx.mascot(q, x, y, eye=ctx.look(1))
    ctx.caption("binding the seventh pane")


def register(anim, world):
    anim.idle_job("confer", weight=99, caption="binding the seventh pane", draw=confer, eye=1)
    anim.key("p", lambda ctx: None, help="possess a pane")
    anim.key("g", lambda ctx: None, help="gate")
'''


def plant_common(root):
    for i, (kind, rarity, scope, cat, note) in enumerate(MOCK_QUEUE):
        write(os.path.join(root, "queue", "%s-%08d.json" % (kind, i)), {
            "id": "%s-%08d" % (kind, i), "kind": kind, "status": "queued", "queued": "2026-09-0%dT10:00:00" % (i + 1),
            "note": note,
            "spec": {"seed": "mock%d" % i, "id": "%08d" % i, "rarity": rarity, "scope": scope, "category": cat,
                     "mood": ["haunted", "cosy", "feral", "smug", "electric", "solemn"][i],
                     "constraint": ["must involve sound", "must react to the size of the pane", "must involve another zellij pane",
                                    "no constraint", "must leave a trace after it ends", "must involve counting"][i],
                     "twist": "the item is alive and has opinions" if rarity == "legendary" else None,
                     "theme": ["patent", "figure", "export", "pdf"], "requires": {"level": 5 * (i + 1), "stats": {}}},
        })


def plant_talents(root):
    for f in os.listdir(os.path.join(root, "talents")):
        p = os.path.join(root, "talents", f)
        if f.endswith(".json"):
            os.remove(p)
    for nid, name, kind, parent, pos, hint in MOCK_TALENTS:
        write(os.path.join(root, "talents", nid + ".json"), {
            "id": nid, "name": name, "kind": kind, "cost": 0 if nid == "root" else (2 if kind == "skill" else 1),
            "parent": parent, "pos": pos, "hint": hint, "effect": {}, "generated": True})


def plant_level117(root):
    for iid, name, flavor, code, rarity in (
        ("crown", "Crown of Closed Tabs", "Every tab he ever closed, remembered as a point of light. It hums.", CROWN, "legendary"),
        ("halo", "Static Halo", "A ring of dead pixels from a pane that was possessed too long.", HALO, "epic"),
        ("familiar", "The Familiar", "It came out of terminal_12 and did not go back. It knows your PR titles.", FAMILIAR, "legendary"),
    ):
        d = os.path.join(root, "items", iid)
        write(os.path.join(d, "item.json"), {"id": iid, "name": name, "flavor": flavor, "category": "cosmetic", "rarity": rarity,
                                             "requires": {"level": 90, "stats": {}}, "attach": {"register": {"import": "job.py"}}})
        write(os.path.join(d, "job.py"), code)


# ── shots ─────────────────────────────────────────────────────────────────
def app_for(ui, state, st_patch=None, frames=90, seed=7):
    random.seed(seed)
    st = state.default_state()
    if st_patch:
        st.update(st_patch)
    state.save(st)
    app = ui.App(headless=True)
    app.branch = "trial1"
    s = ui.Screen(COLS, ROWS)
    app.screen = s
    app.guy.reset(s)
    for _ in range(frames):
        app.frame(s, 1 / 30)
    return app, s


def shot(app, s, page, frames=2):
    app.page = page
    for _ in range(frames):
        app.frame(s, 1 / 30)
    return s


def main():
    root = make_copy()
    ui, state, screen = load_game(root)
    P = screen.P

    # 1. the start
    app, s = app_for(ui, state, frames=95)
    app.guy.mode = "do"
    app.guy.job = "types"
    app.guy.store = {}
    for _ in range(70):
        app.frame(s, 1 / 30)
    render(shot(app, s, "home"), P, os.path.join(OUT, "start.png"))

    # 2. the forge
    plant_common(root)
    app, s = app_for(ui, state, {"level": 9, "xp": 2700}, frames=5)
    render(shot(app, s, "forge"), P, os.path.join(OUT, "forge.png"))

    # 3. a grown talent graph
    plant_talents(root)
    app, s = app_for(ui, state, {"level": 27, "xp": 14000, "owned_talents": MOCK_OWNED,
                                 "unspent": {"stat": 6, "talent": 2}}, frames=5)
    app.tcursor = "passport"
    render(shot(app, s, "talents"), P, os.path.join(OUT, "talents.png"))

    # 4. level 117
    plant_level117(root)
    app, s = app_for(ui, state, {
        "level": 117, "xp": 126_600, "slots": 6,
        "stats": {"vigor": 41, "focus": 188, "craft": 63, "wit": 77, "luck": 29, "charm": 52},
        "equipped": ["laptop", "mug", "book", "crown", "halo", "familiar"],
        "unspent": {"stat": 0, "talent": 1},
    }, frames=40)
    app.guy.mode = "do"
    app.guy.job = "confer"
    app.guy.store = {}
    for _ in range(50):
        app.frame(s, 1 / 30)
    app.guy.say("the panes remember me", 30)
    app.toast("possessed terminal_12 for 9s", "mauve", 60)
    app.toast("a legendary drop from merged PatentCopilot#31337", "peach", 60)
    for _ in range(3):
        app.frame(s, 1 / 30)
    render(s, P, os.path.join(OUT, "level117.png"))

    shutil.rmtree(os.path.dirname(root), ignore_errors=True)


if __name__ == "__main__":
    main()
