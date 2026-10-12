#!/usr/bin/env python3
"""Collect release evidence into a task bundle for cog-collab-docs-drafter.

This runs OUTSIDE the Cog. The Cog never touches GitHub: it only reads the
bundle this script writes. Collection is a host step (see the Frame's
"Host collection is governed by the work contract"), so it is kept here,
separate from the package.

    python tools/collect_evidence.py \
        --repo openteams-ai/apollo-desktop \
        --previous 0.7.1 --target 0.7.2 \
        --out cog-collab-docs-drafter/examples/sample-bundle.json

Requires the GitHub CLI (`gh`), already authenticated with read access to the
repository. Standard library only.

What it gathers for the tag range previous..target:
  - every merged pull request that brought a commit into the range (pr-N);
  - issues those pull requests close (issue-N);
  - commits that reached the range without a pull request (commit-<sha7>);
  - the GitHub release for the target tag, with its asset names (release-<tag>).

Each source keeps its URL so a reviewer can open the original. Author names
are deliberately not collected.
"""
import argparse
import datetime
import json
import subprocess
import sys

DEFAULT_MAX_CHARS = 8000


def gh_json(args):
    """Run `gh` and parse its JSON output. Returns None on a 404."""
    proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        if "Not Found" in proc.stderr or "HTTP 404" in proc.stderr:
            return None
        sys.exit(f"gh {' '.join(args)} failed:\n{proc.stderr.strip()}")
    return json.loads(proc.stdout) if proc.stdout.strip() else None


def headline(message):
    return (message or "").split("\n", 1)[0].strip()


def truncate(text, limit):
    """Cut text to `limit` characters. Returns (text, was_truncated)."""
    if len(text) <= limit:
        return text, False
    return text[:limit].rstrip() + "\n[... truncated by collector ...]", True


def channel_for(release):
    if release is None:
        return "unknown"
    return "prerelease" if release.get("prerelease") else "stable"


def group_commits_by_pr(commits, prs_for_commit):
    """Split range commits into {pr_number: [commit, ...]} and commits with no
    merged pull request. `prs_for_commit(sha)` returns the PR list GitHub
    associates with a commit."""
    by_pr, orphans = {}, []
    for c in commits:
        merged = [p for p in (prs_for_commit(c["sha"]) or []) if p.get("merged_at")]
        if not merged:
            orphans.append(c)
            continue
        for p in merged:
            by_pr.setdefault(p["number"], []).append(c)
    return by_pr, orphans


def pr_source(pr, commits, limit):
    lines = [f"Pull request #{pr['number']}: {pr['title']}",
             f"Merged: {pr.get('mergedAt') or 'unknown'} into {pr.get('baseRefName') or 'unknown'}"]
    labels = [lbl["name"] for lbl in pr.get("labels") or []]
    if labels:
        lines.append("Labels: " + ", ".join(labels))
    lines.append("Commits from this pull request in the release range:")
    lines += [f"- {c['sha'][:7]} {headline(c['commit']['message'])}" for c in commits]
    lines += ["", (pr.get("body") or "(no description)").strip()]
    text, cut = truncate("\n".join(lines), limit)
    return {"id": f"pr-{pr['number']}", "kind": "pull_request", "title": pr["title"],
            "url": pr["url"], "text": text}, cut


def issue_source(issue, limit):
    lines = [f"Issue #{issue['number']}: {issue['title']}",
             f"State: {issue.get('state', 'unknown')}"]
    labels = [lbl["name"] for lbl in issue.get("labels") or []]
    if labels:
        lines.append("Labels: " + ", ".join(labels))
    lines += ["", (issue.get("body") or "(no description)").strip()]
    text, cut = truncate("\n".join(lines), limit)
    return {"id": f"issue-{issue['number']}", "kind": "issue", "title": issue["title"],
            "url": issue["url"], "text": text}, cut


def commit_source(repo, c, limit):
    sha = c["sha"]
    lines = [f"Commit {sha[:7]} (no merged pull request found)",
             f"Committed: {c['commit']['committer']['date']}",
             "", c["commit"]["message"].strip()]
    text, cut = truncate("\n".join(lines), limit)
    return {"id": f"commit-{sha[:7]}", "kind": "commit", "title": headline(c["commit"]["message"]),
            "url": f"https://github.com/{repo}/commit/{sha}", "text": text}, cut


def release_source(release, limit):
    lines = [f"GitHub release {release.get('name') or release['tag_name']} (tag {release['tag_name']})",
             f"Published: {release.get('published_at') or 'not published'}",
             f"Prerelease: {str(bool(release.get('prerelease'))).lower()}",
             f"Draft: {str(bool(release.get('draft'))).lower()}",
             f"Target: {release.get('target_commitish') or 'unknown'}",
             "Assets:"]
    assets = [a["name"] for a in release.get("assets") or []]
    lines += [f"- {name}" for name in assets] or ["- (none)"]
    lines += ["", "Release body:", (release.get("body") or "(empty)").strip()]
    text, cut = truncate("\n".join(lines), limit)
    return {"id": f"release-{release['tag_name']}", "kind": "release",
            "title": release.get("name") or release["tag_name"],
            "url": release["html_url"], "text": text}, cut


def collect(repo, previous, target, product, limit, channel_override=None):
    target_commit = gh_json(["api", f"repos/{repo}/commits/{target}", "--jq", "{sha: .sha}"])
    if target_commit is None:
        sys.exit(f"target tag {target!r} not found in {repo}")
    compare = gh_json(["api", f"repos/{repo}/compare/{previous}...{target}"])
    if compare is None:
        sys.exit(f"cannot compare {previous}...{target} in {repo}")
    commits = compare.get("commits") or []
    notes = []
    if compare.get("total_commits", len(commits)) > len(commits):
        notes.append(f"Only {len(commits)} of {compare['total_commits']} commits in the range were "
                     "returned by GitHub; some changes may be missing from this bundle.")

    by_pr, orphans = group_commits_by_pr(
        commits, lambda sha: gh_json(["api", f"repos/{repo}/commits/{sha}/pulls"]))

    sources, truncated, issue_numbers = [], [], []
    for number in sorted(by_pr):
        pr = gh_json(["pr", "view", str(number), "-R", repo, "--json",
                      "number,title,body,url,mergedAt,baseRefName,labels,closingIssuesReferences"])
        src, cut = pr_source(pr, by_pr[number], limit)
        sources.append(src)
        truncated += [src["id"]] if cut else []
        issue_numbers += [i["number"] for i in pr.get("closingIssuesReferences") or []]

    for number in sorted(set(issue_numbers)):
        issue = gh_json(["issue", "view", str(number), "-R", repo, "--json",
                         "number,title,body,url,state,labels"])
        if issue:
            src, cut = issue_source(issue, limit)
            sources.append(src)
            truncated += [src["id"]] if cut else []

    for c in orphans:
        src, cut = commit_source(repo, c, limit)
        sources.append(src)
        truncated += [src["id"]] if cut else []

    release = gh_json(["api", f"repos/{repo}/releases/tags/{target}"])
    if release is None:
        notes.append(f"No GitHub release exists for tag {target}; publication date, channel and "
                     "downloads are unknown.")
    else:
        src, cut = release_source(release, limit)
        sources.append(src)
        truncated += [src["id"]] if cut else []

    if truncated:
        notes.append(f"These sources were cut to {limit} characters: {', '.join(truncated)}.")

    bundle = {
        "release": {
            "product": product,
            "repository": repo,
            "previous_tag": previous,
            "target_tag": target,
            "target_commit": target_commit["sha"],
            "channel": channel_override or channel_for(release),
        },
        "collection": {
            "tool": "tools/collect_evidence.py",
            "collected_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "range_commits": len(commits),
        },
        "sources": sources,
    }
    if notes:
        bundle["notes"] = " ".join(notes)
    return bundle


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", default="openteams-ai/apollo-desktop")
    ap.add_argument("--previous", required=True, help="tag of the previous release")
    ap.add_argument("--target", required=True, help="tag of the release to document")
    ap.add_argument("--product", default="Collab Desktop")
    ap.add_argument("--channel", choices=["stable", "prerelease", "unknown"],
                    help="override the channel read from the GitHub release")
    ap.add_argument("--max-chars", type=int, default=DEFAULT_MAX_CHARS,
                    help="cap on each source's text (default %(default)s)")
    ap.add_argument("--out", help="write the bundle here (default: stdout)")
    args = ap.parse_args()

    bundle = collect(args.repo, args.previous, args.target, args.product,
                     args.max_chars, args.channel)
    text = json.dumps(bundle, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"wrote {len(bundle['sources'])} sources to {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
