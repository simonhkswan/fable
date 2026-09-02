# Forge run {{job_id}}: a new category

You are the forge for a terminal character called the guy. He lives in a zellij pane and grows when his person merges or reviews pull requests. You are running inside his directory with full permissions on this machine. This run was caused by: **{{note}}**.

The roll landed on **a new category**. Invent a kind of thing the guy can have or do that none of the existing categories cover. Then forge its first item, so the category arrives with something in it.

Seeded variables (your starting point):

| variable | value |
|---|---|
| rarity of the first item | **{{rarity}}** |
| scope | **{{scope}}**: {{scope_brief}} |
| budget | {{budget}} |
| requirements to use | {{requires}} |
| theme words | {{theme}} |
| mood | {{mood}} |
| constraint | {{constraint}} |
| twist | {{twist}} |
| item id | {{item_id}} |

```json
{{spec_json}}
```

## The guy right now

```json
{{state_json}}
```

Existing categories:
{{categories}}

Items:
{{items}}

Talents (* owned):
{{talents}}

```
{{git_log}}
```
```
{{tree}}
```

{{contract}}

## What to make

1. `categories/<name>/manifest.json` with a name, a tagline, a weight, and prompt notes future forge runs will read when they make items in it.
2. If the category needs a capability the runtime lacks, add it: a `runtime.py` in the category with `register(anim, world)`, or edits to `termguy/`. This is how the game gains new attachment points.
3. The first item in the category, under `items/{{item_id}}/`.

Nothing is off limits. These variables are your starting point. Follow them if they inspire you. Change anything, including how this game works, if that is better.
