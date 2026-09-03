"""The animation registries. Items and categories register into these to give
Fable new things to do, wear, say and react to.

    def register(anim, world):
        anim.idle_job("sharpen", weight=2, caption="sharpening", draw=sharpen)
        anim.layer("cape", z=1, draw=draw_cape)
        anim.reaction("level_up", play=flourish)
        anim.palette("clay", (120, 80, 200))
        anim.key("c", on_c)
        anim.tick(every_frame)

Draw functions receive a Ctx (see below), a Quad, and quarter-cell coordinates.
"""
import math
import random
from . import screen as SC
from .screen import P
from . import clock as _clock


class Ctx:
    """What a draw function gets. Wraps the mascot's own drawing helpers so an
    item draws in the same idiom as the built-in jobs."""

    def __init__(self, guy):
        self.guy = guy
        self.P = P
        self.q = None            # the Quad of the current frame, for reactions

    # geometry
    @property
    def u(self): return self.guy.u
    @property
    def k(self): return self.guy.k
    @property
    def t(self): return self.guy.t
    @property
    def dt(self): return self.guy.dt
    @property
    def screen(self): return self.guy.screen
    @property
    def state(self): return self.guy.state
    @property
    def clock(self):
        """The time of day: hour, minute, phase, sun, az, dark, text. See fable/clock.py."""
        return _clock.now()
    @property
    def store(self):
        """Per-job scratch dict, cleared when the job changes."""
        return self.guy.store

    # drawing
    def cell(self, q, x, y, name): self.guy._cell(q, x, y, name)
    def block(self, q, x, y, rgb): self.guy._block(q, x, y, rgb)
    def grid(self, q, x, y, rows, ink=None): self.guy._grid(q, x, y, rows, ink)
    def fade(self, name, f): return self.guy._fade(name, f)
    def burst(self, x, y, n, inks): self.guy._burst(x, y, n, inks)
    def sparks(self, q): self.guy._sparks(q)
    def look(self, base): return self.guy._look(base)
    def mascot(self, q, x, y, **kw): self.guy._mascot(q, x, y, **kw)
    def text(self, x, y, s, ink="subtext0"):
        """Plain text in terminal cells, not quarter cells."""
        self.guy.screen.text(x, y, s, SC.named(ink))
    def caption(self, text): self.guy.caption_override = text


class Anim:
    def __init__(self):
        self.idle_jobs = {}      # name -> {weight, caption, draw, eye}
        self.layers = []         # (z, name, draw)
        self.reactions = {}      # event -> [play]
        self.keys = {}           # char -> (fn, help)
        self.ticks = []          # fn(ctx)
        self.pages = {}          # key -> (title, draw(ctx, screen), keys(ctx, key))
        self.errors = []

    def idle_job(self, name, weight=1, caption=None, draw=None, eye=0):
        self.idle_jobs[name] = {"weight": weight, "caption": caption or name, "draw": draw, "eye": eye}

    def remove_idle_job(self, name):
        self.idle_jobs.pop(name, None)

    def layer(self, name, z=0, draw=None):
        self.layers = [l for l in self.layers if l[1] != name]
        self.layers.append((z, name, draw))
        self.layers.sort(key=lambda l: l[0])

    def reaction(self, event, play):
        """play(ctx, data) is called once when the event fires. It may return
        a generator; the generator is then stepped once per frame until it
        ends, and ctx.q is the Quad for the current frame."""
        self.reactions.setdefault(event, []).append(play)

    def palette(self, name, rgb):
        P[name] = tuple(rgb)

    def key(self, char, fn, help=""):
        self.keys[char] = (fn, help)

    def tick(self, fn):
        self.ticks.append(fn)

    def page(self, key, title, draw, keys=None):
        """A whole page of the widget, like the bag or the talent graph."""
        self.pages[key] = (title, draw, keys)

    def fail(self, where, exc):
        self.errors.append("%s: %s" % (where, exc))
        del self.errors[:-20]
