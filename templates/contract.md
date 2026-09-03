## How the widget reaches code

Everything lives under `~/.termguy`. The widget is `./guy` (Python 3.14, stdlib only so far). Package: `termguy/`.

An **item** is a directory `items/<id>/` with `item.json` (the four he starts with live in `starter/` and follow the same shape):

```json
{
  "id": "<id>", "name": "...", "flavor": "one or two sentences",
  "category": "<category>", "rarity": "<rarity>",
  "requires": {"level": N, "stats": {"focus": N}},
  "attach": {
    "register":        {"import": "thing.py"},
    "key:x":           {"run": "./cast.sh", "help": "what x does"},
    "event:pr_merged": {"run": "uv run --script celebrate.py"},
    "tick":            {"stream": "node aura.js"}
  },
  "build": "optional shell command, run once by you now"
}
```

Three ways to reach code. Mix them freely, any language:

- `import` (Python, in-process). For `register`, the module defines `register(anim, world)`. For `key:x`, `event:<name>` or `tick`, it defines `main(ctx, world[, data])`.
- `run` (any language). Started with the shell, cwd = the item dir, non-blocking. Env: `GUY_DIR`, `GUY_ITEM_DIR`, `GUY_STATE`, `GUY_PANE_ID`, `GUY_COLS`, `GUY_ROWS`, and `GUY_EVENT` (JSON) for events.
- `stream` (any language). Started once when equipped, kept alive. Receives one JSON line per frame on stdin: `{"t","dt","u","x","y","w","h","job"}` (x, y in quarter cells, u = quarter cells per sprite pixel). Replies with JSON lines `{"cells": [[qx, qy, "ink"], ...], "text": [[col, row, "str", "ink"]], "say": "..."}` and the widget draws the latest reply each frame.

Attachment points that exist now: `register`, `key:<char>`, `tick`, `equip`, `event:pr_merged`, `event:review`, `event:level_up`, `event:drop`, `event:equip`, `event:unequip`, `event:idle`. You may add more by editing `termguy/`.

### The animation API (`register(anim, world)`)

```python
def register(anim, world):
    anim.idle_job("sharpen", weight=2, caption="sharpening", draw=sharpen, eye=1)   # a new thing to do when idle
    anim.layer("cape", z=1, draw=draw_cape)      # z<0 behind the body, z>=0 in front. draw(ctx, q, pose)
    anim.reaction("level_up", play=flourish)     # play(ctx, data) -> None or a generator stepped per frame; ctx.q is the Quad
    anim.palette("clay", (120, 80, 200))         # recolour anything by name
    anim.key("c", on_c, help="cast")             # on_c(ctx)
    anim.tick(every_frame)                       # every_frame(ctx)
    anim.page("w", "Weather", draw_page, keys=on_key)  # a whole page: draw(ctx, screen), on_key(ctx, key) -> bool handled
```

Idle job draw signature: `draw(ctx, q, x, y, floor_y)`, all in quarter cells. Look at `termguy/mascot.py` for the six built-in jobs and copy their idiom. `ctx` gives: `ctx.u ctx.k ctx.t ctx.dt ctx.screen ctx.state ctx.store ctx.P` and helpers `ctx.cell(q,x,y,ink) ctx.block(q,x,y,rgb) ctx.grid(q,x,y,rows,ink_map) ctx.fade(ink,f) ctx.burst(x,y,n,inks) ctx.sparks(q) ctx.look(eye) ctx.mascot(q,x,y,eye=,lean=,legs=,squash=,shut=) ctx.text(col,row,str,ink) ctx.caption(str)`. `ctx.guy.say("hi", 4.0)` shows a speech bubble. `ctx.guy.fire("name", **data)` fires a moment.

Inks are names in `termguy/screen.py:P` (Catppuccin Macchiato plus `clay`). `pose` has `x y eye lean squash shut u`.

### The world (`world`)

`world.zellij(*args)` runs `zellij action ...`. `world.list_panes()`, `world.open_portal([cmd...], x, y, width, height, name, focus, borderless)` returns a pane id and records it, `world.glide(pane_id, x, y, width, height)`, `world.possess(pane_id, [cmd...])` runs a command in place of another pane and gives it back on exit, `world.close_owned()`, `world.sh(cmd)`, `world.claude(prompt)`, `world.say(text)`, `world.state` / `world.save()`, `world.remember(text)`. The guy's own pane id: `world.pane_id`. The session: `world.session`. You can also just call `subprocess`.

### Talent nodes

`talents/<id>.json`: `{"id","name","hint","kind":"passive"|"skill","cost","parent","pos":[x,y],"effect":{...},"generated":false}`. Effects: `{"stat":{"focus":1}}`, `{"slots":1}`, `{"budget":{"travel":5}}`, `{"discount":{"travel":1}}`, `{"weight":{"cosmetic":2}}`. A skill node also has a directory `talents/<id>/` with an `item.json` like an item, minus requirements. Positions are a rough grid around root at [0,0]; keep new nodes adjacent to their parent.

### Categories

`categories/<name>/manifest.json`: `{"name","tagline","weight","hooks":[...],"prompt_notes":"..."}`. A category may also hold `runtime.py` with `register(anim, world)`; the widget imports every category runtime at start, so a category can add attachment points, pages or verbs that later items use.

### Before you finish

Run `./guy boot-test`. It must exit 0. It renders 300 frames headless, opens every page, fires every event, equips every item whose requirements are met, and prints any errors items raised. Then leave the working tree as you want it committed; the forge commits for you.
