# Fable

A small character who lives in a terminal pane and grows into a story. He grows when you merge a pull request or review one. What he becomes is written by an LLM, one forge run at a time, so no two guys are the same. Individual experiences will vary.

![the start](docs/screenshots/start.png)

## What he does

- He idles in his pane: ships code, makes a brew, reads the docs, juggles, thinks, naps.
- Every merged PR and every review gives him xp. Some give a stat. A few drop a thing.
- Every 5 levels he gets a thing. Every 3 levels he gets a talent point.
- Things arrive unopened. You open one at the forge. One forge run is one Claude Code session that writes the item, its code, and its flavor text.
- Items have requirements. You can hold a thing for a long time before he can use it.
- The talent graph grows where you spend. A new branch is generated when you buy a node.
- Items can do anything the forge can code: wear a hat, change his colours, walk across your screen in a floating pane, take over another pane for a moment, or rewrite how the game works.

## Start

```
fable --branch trial1
```

The first start pulls your GitHub history and replays it, one event at a time. Then he keeps syncing every 10 minutes.

## Keys

| key | page |
|---|---|
| `b` | bag: what he has, what he wears, what he cannot use yet |
| `t` | talents: the graph, and where to spend points |
| `s` | stats: spend stat points |
| `f` | forge: open unopened things |
| `l` | log: what happened |
| `i` | info |
| `?` | report: type a bug or a wish, press enter, and a forge run fixes it |
| `q` | quit |

Items add their own keys. The bottom line shows them.

## Saves are branches

`main` holds the code. A save is a git branch. `fable --branch <name>` starts a save, or makes a new one from main. Everything the forge writes is committed on the save branch. `fable upgrade` merges new code from main into the save. `fable saves` lists them.

## How the dice work

Every event has a seed. A merged PR seeds from its merge commit SHA. From that seed come the xp, the stat gain, the drop, its rarity, its budget, its requirements, its category, and a mood, a constraint, and a twist for the forge. The same history always rolls the same. The odds live in `tables/` as JSON.

The forge gets those numbers as a starting point, and the brief ends with the same line every time:

> These variables are your starting point. Follow them if they inspire you. Change anything, including how this game works, if that is better.

Nothing in this directory is off limits to a forge run. Item code runs with your permissions, in any language. The forge commits before and after each run, so `git log` on a save is the story of your guy, and any run can be undone.

## What it can look like

These are illustrations rendered through the real pages with made-up content. Your guy will not look like this. He will look like something else.

A talent graph after some months:

![a talent graph](docs/screenshots/talents.png)

The forge page with things waiting:

![the forge](docs/screenshots/forge.png)

A guy at level 117:

![level 117](docs/screenshots/level117.png)

## Commands

```
fable --branch <save>   run on a save branch
fable sync              pull new events now
fable queue             list unopened things
fable forge             open the next thing from the shell
fable brief <job>       print the brief a forge run would get
fable status            one screen of text
fable upgrade           merge main into this save
fable cleanup           close panes he opened and forgot
fable boot-test         headless check that the widget boots
```

## Requirements

- Python 3.14, standard library only for the widget itself
- `gh`, logged in
- `claude`, logged in, for forge runs
- zellij, for the travel and possession items. He runs in any terminal without it.
