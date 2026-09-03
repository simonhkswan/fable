# ~/.fable

This directory is a game. A terminal character called Fable lives in a zellij pane and grows when his person merges or reviews pull requests. Forge runs are Claude Code sessions started here with a brief in `runs/*/forge-brief.md`. If you are one of those sessions, the brief you were given is the task. Nothing in this directory is off limits to you.

## Layout

- `bin/fable` — the entry point. `fable` runs the widget, `./bin/fable boot-test` checks it boots.
- `fable/` — the package. `ui.py` pages and loop, `mascot.py` the sprite and built-in idle jobs, `anim.py` registries items extend, `items.py` how manifests reach code, `world.py` zellij and the outside, `rules.py` growth arithmetic and seeded rolls, `sync.py` GitHub events to growth, `forge.py` runs briefs, `talents.py` the graph.
- `tables/` — odds and curves, as JSON.
- `templates/` — the briefs forge runs receive, and `contract.md` that describes the code contract.
- `categories/<name>/` — a manifest and an optional `runtime.py`.
- `items/<id>/` — a manifest and code, any language. `starter/` holds the four he begins with.
- `talents/<id>.json` — graph nodes. Skills also have `talents/<id>/`.
- `state.json`, `events.jsonl`, `spending.jsonl` — Fable's state, the events consumed, the points spent.
- `queue/` — unopened things, one JSON per forge job. `runs/` — briefs and transcripts.

## Rules of thumb for a forge run

- Read `fable/mascot.py` before drawing. Move the way he moves.
- Put things in the bag with real names and flavor text. Requirements from the spec go in `item.json`.
- Run `./bin/fable boot-test` before you finish. Exit code 0 or the run is undone.
- The forge commits for you. Do not commit yourself.
- Python here is 3.14 with only the stdlib. Other languages: `node`, `uv`, `bash` are installed.

## Branches

`main` is the development branch and holds only the code, tables, templates, seed categories and seed talents. Every save of Fable is a branch. `fable <name>` checks it out, creating it from main if new. Forge runs refuse to run on main, and their commits land on the save branch. `fable upgrade` merges main into the current save.
