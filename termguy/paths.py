import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "state.json")
EVENTS = os.path.join(ROOT, "events.jsonl")       # every consumed event and its rolls
SPENDING = os.path.join(ROOT, "spending.jsonl")   # every point you spent, append only
TABLES = os.path.join(ROOT, "tables")
TEMPLATES = os.path.join(ROOT, "templates")
CATEGORIES = os.path.join(ROOT, "categories")
ITEMS = os.path.join(ROOT, "items")
TALENTS = os.path.join(ROOT, "talents")
QUEUE = os.path.join(ROOT, "queue")               # forge jobs not yet run
RUNS = os.path.join(ROOT, "runs")                 # forge transcripts
PRESENCE = os.path.join(ROOT, "presence.json")    # which pane the guy is in right now
LOG = os.path.join(ROOT, "guy.log")


def ensure():
    for d in (TABLES, TEMPLATES, CATEGORIES, ITEMS, TALENTS, QUEUE, RUNS):
        os.makedirs(d, exist_ok=True)
