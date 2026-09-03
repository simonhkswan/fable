"""Starter item. The drawing lives in fable/mascot.py; this item is what lets him do it."""


def register(anim, world):
    anim.idle_job("types", weight=3, caption="shipping code", eye=1,
                  draw=lambda ctx, q, x, y, fy: ctx.guy._types(ctx, q, x, y, fy))
