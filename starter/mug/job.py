"""Starter item. The drawing lives in termguy/mascot.py; this item is what lets him do it."""


def register(anim, world):
    anim.idle_job("coffee", weight=2, caption="making a brew", eye=1,
                  draw=lambda ctx, q, x, y, fy: ctx.guy._coffee(ctx, q, x, y, fy))
