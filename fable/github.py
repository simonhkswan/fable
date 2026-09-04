"""Events from GitHub, through gh. One event per merged PR you wrote and one per
PR you reviewed."""
import json
import subprocess
from .log import log

USER = None


def gh(*args, timeout=60):
    p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("gh %s: %s" % (" ".join(args[:3]), p.stderr.strip()[:300]))
    return p.stdout


def me():
    global USER
    if USER is None:
        USER = gh("api", "user", "-q", ".login").strip()
    return USER


def search(query, limit=1000):
    out = gh("search", "prs", "--limit", str(limit), "--json",
             "number,repository,title,closedAt,updatedAt,url", *query)
    return json.loads(out)


def merged_prs(since=None):
    q = ["--author", me(), "--merged"]
    if since:
        q += ["--merged-at", ">=" + since]
    return search(q)


def reviewed_prs(since=None):
    # Flags must come before the "--" that starts the free-text query. A flag
    # placed after it becomes a search word and the search returns nothing.
    q = ["--reviewed-by", me()]
    if since:
        q += ["--updated", ">=" + since]
    q += ["--", "-author:" + me()]
    return search(q)


def pr_detail(repo, number):
    out = gh("pr", "view", str(number), "--repo", repo, "--json",
             "additions,deletions,changedFiles,mergeCommit,mergedAt,files,reviews,state")
    return json.loads(out)


def event_from_pr(row):
    repo = row["repository"]["nameWithOwner"]
    n = row["number"]
    d = pr_detail(repo, n)
    sha = (d.get("mergeCommit") or {}).get("oid") or ("pr:%s#%d" % (repo, n))
    return {
        "id": "pr:%s#%d" % (repo, n), "kind": "pr", "repo": repo, "number": n,
        "title": row["title"], "url": row["url"], "at": d.get("mergedAt") or row["closedAt"],
        "seed": sha, "additions": d.get("additions", 0), "deletions": d.get("deletions", 0),
        "files": d.get("changedFiles", 0), "paths": [f["path"] for f in d.get("files", [])][:40],
    }


def event_from_review(row):
    repo = row["repository"]["nameWithOwner"]
    n = row["number"]
    d = pr_detail(repo, n)
    mine = [r for r in d.get("reviews", []) if (r.get("author") or {}).get("login") == me()]
    comments = 0
    first = None
    for r in mine:
        comments += len((r.get("body") or "").split()) // 12
        if first is None or (r.get("submittedAt") or "") < first:
            first = r.get("submittedAt")
    ident = "review:%s#%d" % (repo, n)
    return {
        "id": ident, "kind": "review", "repo": repo, "number": n,
        "title": row["title"], "url": row["url"], "at": first or row["updatedAt"],
        "seed": ident + ":" + (first or ""), "comments": comments, "reviews": len(mine),
        "paths": [f["path"] for f in d.get("files", [])][:40],
        "state": d.get("state"),
    }


def iter_new(seen, since=None, progress=None):
    """Yield events not in `seen`, oldest first, one at a time as their details
    arrive. The order comes from the search timestamps, so a caller can apply
    each event the moment it appears."""
    rows = []
    for row in merged_prs(since):
        rows.append(("pr", row, row.get("closedAt") or row.get("updatedAt") or ""))
    for row in reviewed_prs(since):
        rows.append(("review", row, row.get("updatedAt") or ""))
    todo = [(k, r, t) for k, r, t in rows
            if "%s:%s#%d" % (k, r["repository"]["nameWithOwner"], r["number"]) not in seen]
    todo.sort(key=lambda x: x[2])
    for i, (kind, row, _) in enumerate(todo):
        ident = "%s:%s#%d" % (kind, row["repository"]["nameWithOwner"], row["number"])
        if progress:
            progress(i + 1, len(todo), "%s %s#%d  %s" % ("merged" if kind == "pr" else "reviewed",
                                                        row["repository"]["name"], row["number"], row["title"][:40]))
        try:
            ev = event_from_pr(row) if kind == "pr" else event_from_review(row)
        except Exception as e:  # noqa: BLE001
            log("fetch %s failed: %s" % (ident, e))
            continue
        if kind == "review" and ev.get("reviews", 0) == 0:
            continue
        yield ev


def fetch_new(seen, since=None, progress=None):
    """All new events, oldest first."""
    return list(iter_new(seen, since=since, progress=progress))
