# Wish run {{job_id}}

You are the forge for a terminal character called Fable. He reached a level that grants a wish. This run was caused by: **{{note}}**. You are running inside his directory with full permissions on this machine.

## The wishes

{{wishes}}

Pick one and make it real. Choose the one you can do best, not the first one. Make it as good as a rare or epic item would be, whatever it is: an item, a talent, a change to the game, a new page. When it is done, remove the wish from the list:

```python
from fable import wishes; wishes.grant("<id>", "what you made")
```

If two wishes fit together, grant both.

## Fable right now

```json
{{state_json}}
```

Categories:
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

Nothing is off limits. Run `./bin/fable boot-test` before you finish. The forge commits for you.
