import time
from . import paths


def log(msg):
    with open(paths.LOG, "a") as f:
        f.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), msg))
