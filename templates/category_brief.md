# Forge run {{job_id}}: a new category

You are the forge for a terminal character called Fable. He lives in a zellij pane and grows when his person merges or reviews pull requests. You are running inside his directory with full permissions on this machine. This run was caused by: **{{note}}**.

The roll landed on **a new category**. Invent a kind of thing Fable can have or do that none of the existing categories cover. Then forge its first item, so the category arrives with something in it.

Seeded variables (your starting point):

| variable | rolled | what it could have been |
|---|---|---|
| rarity of the first item | **{{rarity}}** | {{rarities}}. Rarity sets the budget, the requirements and the odds of each scope. |
| scope | **{{scope}}** | {{scopes}} |
| budget | {{budget}} | {{budget_range}}. A sense of how much the thing may do or draw: 2 is a hat, 50 is a storm, 90 is a new law of nature. |
| category | {{category}} | {{category_list}}. The category's manifest carries notes for you. |
| requirements to use | {{requires}} | A level near his current one, higher for rarer things, and zero to four stat floors. He keeps the item in the bag until he meets them. |
| theme words | {{theme}} | Words from the PR title, the repo name and the file types it touched. A flavour, not a rule. |
| mood | {{mood}} | One word from a list of twenty, from cosy to feral. The tone of the thing. |
| constraint | {{constraint}} | One line from a list of twenty. A creative limit, or "no constraint". |
| twist | {{twist}} | Usually none. About one run in seven gets a twist that bends the item or the game. |
| item id | {{item_id}} | The directory name under items/. |

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

{{wishes_block}}

{{contract}}

## What to make

1. `categories/<name>/manifest.json` with a name, a tagline, a weight, and prompt notes future forge runs will read when they make items in it.
2. If the category needs a capability the runtime lacks, add it: a `runtime.py` in the category with `register(anim, world)`, or edits to `fable/`. This is how the game gains new attachment points.
3. The first item in the category, under `items/{{item_id}}/`.

Nothing is off limits. These variables are your starting point. Follow them if they inspire you. Change anything, including how this game works, if that is better.
