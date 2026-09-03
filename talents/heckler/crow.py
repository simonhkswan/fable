"""Heckler. A crow that lives a few cells to Fable's left, hops, and is rude.
Drawn as a layer behind the body so it is there no matter what job he does.
The crow talks in its own small line of text. Fable answers in his bubble."""
import math
import random

CROW = ("..##..",
        ".e###r",
        "######",
        ".####.",
        "..#.#.")
CROW_HOP = ("..##..",
            ".e###r",
            "######",
            ".####.",
            ".#...#")
INK = {"#": "surface2", "e": "yellow", "r": "peach"}

JABS = ("seen better.", "again?", "that all?", "nice one.", "bold.", "sure, sure.",
        "caw.", "is this the bit?", "riveting.", "still here.", "who taught you?")
BACK = ("shut it.", "you try it.", "nobody asked.", "watch this.", "jealous.", "fly off.",
        "I heard that.", "and yet you stay.", "caw yourself.")
ON_PR = ("took you long enough.", "merged. big deal.", "fine. that was fine.")
ON_LEVEL = ("still short.", "a whole level. wow.", "do it again then.")
ON_REVIEW = ("you? reviewing?", "harsh. I like it.")

S = {"next": 6.0, "line": None, "until": 0.0, "answer_at": None, "hop": 0.0, "hop_at": 3.0}


def heckle(ctx, line, seconds=3.2, answer=True):
    S["line"] = line
    S["until"] = ctx.t + seconds
    S["answer_at"] = ctx.t + 1.4 if answer else None
    S["next"] = ctx.t + random.uniform(9.0, 16.0)


def draw(ctx, q, pose):
    u = pose["u"]
    t = ctx.t
    if t > S["hop_at"]:
        S["hop_at"] = t + random.uniform(2.0, 5.0)
        S["hop"] = 0.35
    S["hop"] = max(0.0, S["hop"] - ctx.dt)
    lift = int(math.sin(S["hop"] / 0.35 * math.pi) * u) if S["hop"] > 0 else 0
    fy = pose["y"] + 5 * u
    bx = pose["x"] - 9 * u
    by = fy - 5 * u - lift
    ctx.grid(q, bx, by, CROW_HOP if lift else CROW, INK)
    if S["line"] is None and t > S["next"]:
        heckle(ctx, random.choice(JABS))
    if S["line"] is not None:
        if t > S["until"]:
            S["line"] = None
        else:
            col = bx // 2 - len(S["line"]) // 2 + 2
            row = by // 2 - 2
            ctx.text(max(0, col), max(0, row), S["line"], "overlay1")
    if S["answer_at"] is not None and t > S["answer_at"]:
        S["answer_at"] = None
        if not ctx.guy.bubble:
            ctx.guy.say(random.choice(BACK), 2.5)


def on_pr(ctx, data):
    heckle(ctx, random.choice(ON_PR), 4.0, answer=False)


def on_level(ctx, data):
    heckle(ctx, random.choice(ON_LEVEL), 4.0, answer=False)


def on_review(ctx, data):
    heckle(ctx, random.choice(ON_REVIEW), 4.0)


def register(anim, world):
    anim.layer("crow", z=-1, draw=draw)
    anim.reaction("pr_merged", on_pr)
    anim.reaction("level_up", on_level)
    anim.reaction("review", on_review)
