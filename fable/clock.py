"""The clock. The widget keeps the time of day so items can care about it.

    from fable import clock
    c = clock.now()   # {"hour", "minute", "second", "frac", "phase", "sun", "az", "dark", "text"}

phase is one of: small hours (0-5), dawn (5-8), day (8-17), dusk (17-20), night (20-24).
sun is the height of the sun, 0 at 06:00 and 20:00, 1 at 13:00, 0 through the night.
az is where the sun stands, -1 in the east at dawn, +1 in the west at dusk.
dark is True when the sun is down.

Set FABLE_CLOCK=HH:MM to freeze the clock, for screenshots and tests.
The mascot fires `hour` whenever the hour changes and `midnight` at 00:00.
"""
import math
import os
import time

PHASES = (("small hours", 0, 5), ("dawn", 5, 8), ("day", 8, 17), ("dusk", 17, 20), ("night", 20, 24))
SUNRISE, SUNSET = 6.0, 20.0


def phase_of(hour):
    for name, a, b in PHASES:
        if a <= hour < b:
            return name
    return "night"


def now():
    frozen = os.environ.get("FABLE_CLOCK")
    if frozen:
        try:
            h, m = frozen.split(":")[:2]
            h, m, s = int(h) % 24, int(m) % 60, 0
        except ValueError:
            h, m, s = 12, 0, 0
    else:
        lt = time.localtime()
        h, m, s = lt.tm_hour, lt.tm_min, lt.tm_sec
    hours = h + m / 60.0 + s / 3600.0
    f = (hours - SUNRISE) / (SUNSET - SUNRISE)
    if 0.0 <= f <= 1.0:
        sun, az = math.sin(f * math.pi), f * 2.0 - 1.0
    else:
        sun, az = 0.0, 1.0
    return {"hour": h, "minute": m, "second": s, "frac": hours / 24.0,
            "phase": phase_of(h), "sun": sun, "az": az, "dark": sun <= 0.0,
            "text": "%02d:%02d" % (h, m)}
