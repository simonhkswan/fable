"""Starter item. The drawing lives in termguy/mascot.py; this item is what lets him do it."""


def register(anim, world):
    anim.idle_job("thinks", weight=2, caption="thinking about it", eye=1,
                  draw=lambda ctx, q, x, y, fy: ctx.guy._thinks(ctx, q, x, y, fy))
