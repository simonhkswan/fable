"""Starter item. The drawing lives in termguy/mascot.py; this item is what lets him do it."""


def register(anim, world):
    anim.idle_job("juggles", weight=1, caption="juggling", eye=0,
                  draw=lambda ctx, q, x, y, fy: ctx.guy._juggles(ctx, q, x, y, fy))
