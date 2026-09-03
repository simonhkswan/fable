"""Cells, colours and quarter-cell drawing. Lifted from claude-idle."""

CSI = "\x1b["
RESET_FG = CSI + "39m"
RESET_BG = CSI + "49m"

# Catppuccin Macchiato plus Fable's own clay. Items may add or override names
# through anim.palette(), which writes into this same dict.
P = {
    "rosewater": (244, 219, 214), "flamingo": (240, 198, 198),
    "pink": (245, 189, 230), "mauve": (198, 160, 246),
    "red": (237, 135, 150), "maroon": (238, 153, 160),
    "peach": (245, 169, 127), "yellow": (238, 212, 159),
    "green": (166, 218, 149), "teal": (139, 213, 202),
    "sky": (145, 215, 227), "sapphire": (125, 196, 228),
    "blue": (138, 173, 244), "lavender": (183, 189, 248),
    "text": (202, 211, 245), "subtext1": (184, 192, 224),
    "subtext0": (165, 173, 203), "overlay2": (147, 154, 183),
    "overlay1": (128, 135, 162), "overlay0": (110, 115, 141),
    "surface2": (91, 96, 120), "surface1": (73, 77, 100),
    "surface0": (54, 58, 79), "base": (36, 39, 58),
    "mantle": (30, 32, 48), "crust": (24, 25, 38),
    "clay": (181, 111, 86),
}

RARITY_INK = {"common": "subtext0", "rare": "sky", "epic": "mauve",
              "legendary": "peach", "ultra": "lavender", "fix": "teal"}
# rarities drawn with an effect: (base ink, highlight ink)
SHIMMER = {"legendary": ("peach", "rosewater"), "ultra": ("mauve", "rosewater")}

_fg_cache = {}


def fg(r, g, b):
    k = (r, g, b)
    s = _fg_cache.get(k)
    if s is None:
        s = "%s38;2;%d;%d;%dm" % (CSI, r, g, b)
        _fg_cache[k] = s
    return s


def bg(r, g, b):
    return "%s48;2;%d;%d;%dm" % (CSI, r, g, b)


def named(name):
    return fg(*P.get(name, P["text"]))


def named_bg(name):
    return bg(*P.get(name, P["base"]))


BLANK = (" ", None, None)


class Screen:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        n = w * h
        self._blank = [BLANK] * n
        self.cells = list(self._blank)
        self.prev = [None] * n

    def clear(self):
        self.cells[:] = self._blank

    def set(self, x, y, ch, f=None, b=None):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cells[y * self.w + x] = (ch, f, b)

    def text(self, x, y, s, f=None, b=None):
        if not (0 <= y < self.h):
            return
        base = y * self.w
        w = self.w
        for i, ch in enumerate(s):
            cx = x + i
            if 0 <= cx < w:
                self.cells[base + cx] = (ch, f, b)

    def fill(self, x, y, w, h, ch=" ", f=None, b=None):
        for yy in range(y, y + h):
            self.text(x, yy, ch * w, f, b)

    def flush(self, out):
        cells = self.cells
        prev = self.prev
        w = self.w
        parts = []
        add = parts.append
        cur_f = cur_b = "\0"
        for y in range(self.h):
            row = y * w
            x = 0
            placed = False
            while x < w:
                i = row + x
                c = cells[i]
                if c == prev[i]:
                    placed = False
                    x += 1
                    continue
                if not placed:
                    add("%s%d;%dH" % (CSI, y + 1, x + 1))
                    placed = True
                ch, f, b = c
                f = f or RESET_FG
                b = b or RESET_BG
                if f != cur_f:
                    add(f)
                    cur_f = f
                if b != cur_b:
                    add(b)
                    cur_b = b
                add(ch)
                prev[i] = c
                x += 1
        if parts:
            out.write("".join(parts))
            out.flush()


QUAD = (" ", "▗", "▖", "▄", "▝", "▐", "▞", "▟",
        "▘", "▚", "▌", "▙", "▀", "▜", "▛", "█")


class Quad:
    """A canvas of quarter cells. x and y here are in quarter cells: two per
    terminal cell in each direction."""
    __slots__ = ("cells",)

    def __init__(self):
        self.cells = {}

    def rect(self, x, y, w, h, c):
        cells = self.cells
        for sy in range(y, y + h):
            cy = sy >> 1
            half = (sy & 1) << 1
            for sx in range(x, x + w):
                key = (sx >> 1, cy)
                q = cells.get(key)
                if q is None:
                    q = cells[key] = [None, None, None, None]
                q[half | (sx & 1)] = c

    def flush(self, s):
        for (cx, cy), q in self.cells.items():
            a, b, c, d = q
            if a is b and b is c and c is d:
                if a is not None:
                    s.set(cx, cy, "█", fg(*a))
                continue
            best = None
            n = 0
            for v in (a, b, c, d):
                if v is None:
                    continue
                m = (v is a) + (v is b) + (v is c) + (v is d)
                if m > n:
                    best, n = v, m
            if best is None:
                continue
            mask = 0
            other = None
            for i, v in enumerate((a, b, c, d)):
                if v is best:
                    mask |= 8 >> i
                elif v is not None:
                    other = v
            if other is None:
                s.set(cx, cy, QUAD[mask], fg(*best))
            else:
                s.set(cx, cy, QUAD[mask], fg(*best), bg(*other))


# ── text effects ───────────────────────────────────────────────
# Timing taken from the Claude Code shimmer: the bright head moves one
# character every 50 ms, and the sweep runs from 10 characters before the text
# to 10 after, so there is a still moment between passes.

import colorsys


def blend(a, b, f):
    return (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f), int(a[2] + (b[2] - a[2]) * f))


def shimmer_text(s, x, y, text, base, hi, t, b=None, width=3, start=0):
    """Write text in `base` with a pulse of `hi` sweeping through it.
    `t` is seconds. `start` lets several words share one sweep."""
    base_rgb = P.get(base, P["text"]) if isinstance(base, str) else base
    hi_rgb = P.get(hi, P["rosewater"]) if isinstance(hi, str) else hi
    n = len(text)
    cycle = n + 20
    head = -10 + int(t * 20) % cycle - start
    for i, ch in enumerate(text):
        d = abs(i - head)
        f = max(0.0, 1.0 - d / float(width)) if d < width else 0.0
        s.set(x + i, y, ch, fg(*blend(base_rgb, hi_rgb, f * f)), b)


def rainbow_text(s, x, y, text, t, b=None, speed=0.12, spread=0.045, sat=0.55, light=0.68):
    """Write text with a hue that drifts along the word and over time."""
    for i, ch in enumerate(text):
        h = (t * speed + i * spread) % 1.0
        r, g, bb = colorsys.hls_to_rgb(h, light, sat)
        s.set(x + i, y, ch, fg(int(r * 255), int(g * 255), int(bb * 255)), b)


def rarity_text(s, x, y, text, rarity, t, b=None, dim=False):
    """Name text in its rarity's colouring. Legendary and ultra shimmer."""
    if dim:
        s.text(x, y, text, named("overlay0"), b)
        return
    if rarity in SHIMMER:
        base, hi = SHIMMER[rarity]
        shimmer_text(s, x, y, text, base, hi, t, b)
    else:
        s.text(x, y, text, named(RARITY_INK.get(rarity, "text")), b)


def scope_text(s, x, y, text, scope, t, b=None):
    """The word mutate gets the rainbow. Other scopes are plain."""
    if scope == "mutate":
        rainbow_text(s, x, y, text, t, b)
    else:
        s.text(x, y, text, named({"item": "subtext0", "extend": "sky", "rewrite": "mauve"}.get(scope, "text")), b)
