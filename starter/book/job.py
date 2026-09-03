"""Starter item. The drawing lives in termguy/mascot.py; this item is what lets him do it."""


def register(anim, world):
    anim.idle_job("reads", weight=2, caption="reading the docs", eye=1,
                  draw=lambda ctx, q, x, y, fy: ctx.guy._reads(ctx, q, x, y, fy))
