# Forge run {{job_id}}: grow the talent graph

You are the forge for a terminal character called Fable. His person just spent a talent point, and the graph must grow where they spent it. This run was caused by: **{{note}}**.

```json
{{spec_json}}
```

The node just bought is `node` in the spec. Add `neighbours_wanted` new nodes adjacent to it (parent = that node, positions next to its `pos`, not overlapping `existing_nodes`). Roughly three in four should be passive, the rest skills. Passives shape the game: stats, slots, budgets for a category, discounts on requirements, weights that make a category drop more. Skills are permanent abilities forged like items (see contract), in a directory `talents/<id>/` with `item.json`, and cost 2 or 3 points. Name them so the branch reads as a path with a theme that continues the parent's idea, in the mood **{{mood}}**.

## The guy right now

```json
{{state_json}}
```

Categories:
{{categories}}

Talents (* owned):
{{talents}}

Items:
{{items}}

{{wishes_block}}

{{contract}}

Nothing is off limits. If the graph itself needs a new kind of effect, add it to `fable/talents.py`. These variables are your starting point. Follow them if they inspire you. Change anything, including how this game works, if that is better.
