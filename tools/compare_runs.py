#!/usr/bin/env python3
"""Compare saved cog-collab-docs-drafter runs on the same bundle.

    python tools/compare_runs.py --bundle B.json run1.json run2.json ... \
        [--recheck] [--answer-key key.json] [--out report.md]

For each run (an envelope v1 result from `pixi run ask`) it reports latency,
entries and problems by check, then a table of how each run treated every
source: which entry cited it, or why it was excluded, or a gap, or nothing.
That is the variability Prakriti asked us to measure across models and runs.

--recheck re-runs the Cog's CURRENT contract checks on each saved payload
(no model call), so a run made before a check existed can be scored by it.
The Cog's machinery is imported from cog-collab-docs-drafter/src.

--answer-key takes a JSON object {"source-id": "entry" | "excluded" | "gap"}
and counts how many sources each run placed as the key expects. Sources the
key leaves out are not scored.

Run it with the Cog's environment (pyyaml, jsonschema), for example
`pixi run --manifest-path cog-collab-docs-drafter/pixi.toml python tools/compare_runs.py ...`.
"""
import argparse
import collections
import json
import os
import sys
from pathlib import Path

COG = Path(__file__).resolve().parent.parent / "cog-collab-docs-drafter"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def recheck(payload, bundle):
    """The Cog's current validate_output on a saved payload."""
    sys.path.insert(0, str(COG / "src"))
    cwd = os.getcwd()
    try:
        os.chdir(COG)   # the machinery resolves its binding relative to the Cog
        import cog_core
        return cog_core.validate_output(payload, bundle)
    finally:
        os.chdir(cwd)


def placement(payload):
    """source id -> how this run treated it."""
    out = collections.defaultdict(list)
    for e in payload.get("entries") or []:
        for c in e.get("claims") or []:
            for sid in c.get("source_ids") or []:
                tag = f"entry: {e.get('title', '?')[:40]}"
                if tag not in out[sid]:
                    out[sid].append(tag)
    for x in payload.get("excluded") or []:
        for sid in x.get("source_ids") or []:
            out[sid].append(f"excluded ({x.get('reason')})")
    for g in payload.get("gaps") or []:
        for sid in g.get("source_ids") or []:
            tag = f"gap ({g.get('kind')})"
            if tag not in out[sid]:
                out[sid].append(tag)
    for sid in (payload.get("intro") or {}).get("source_ids") or []:
        if sid not in out:
            out[sid].append("intro only")
    release_ids = set((payload.get("release") or {}).get("source_ids") or [])
    for d in payload.get("downloads") or []:
        release_ids.update(d.get("source_ids") or [])
    for sid in sorted(release_ids):
        out[sid].append("release facts")
    return out


def closed_by(bundle):
    """issue id -> pull request ids that close it, as the Cog's coverage
    check sees it."""
    sys.path.insert(0, str(COG / "src"))
    import task_logic
    return task_logic._closers(bundle)


def with_closers(placed, closers):
    """Mark an otherwise unplaced issue as covered by its closing PR."""
    for issue, prs in closers.items():
        if not placed.get(issue):
            hit = sorted(p for p in prs if placed.get(p))
            if hit:
                placed[issue].append(f"via {', '.join(hit)}")
    return placed


def kind_of(tags):
    if any(t.startswith("entry") for t in tags):
        return "entry"
    if any(t.startswith("excluded") for t in tags):
        return "excluded"
    if any(t.startswith("gap") for t in tags):
        return "gap"
    return "none"


def report(bundle, runs, do_recheck, key):
    lines = ["# Run comparison", "",
             f"Bundle: {bundle['release']['repository']} "
             f"{bundle['release']['previous_tag']} → {bundle['release']['target_tag']}, "
             f"{len(bundle['sources'])} sources", ""]
    header = "| | " + " | ".join(name for name, _ in runs) + " |"
    rule = "|---" * (len(runs) + 1) + "|"
    rows = collections.OrderedDict()
    per_run_problems = []
    for name, env in runs:
        payload = env.get("payload") or {}
        binding = env.get("binding") or {}
        problems = recheck(payload, bundle) if (do_recheck and env.get("payload")) else (env.get("problems") or [])
        per_run_problems.append(problems)
        rows.setdefault("Model", []).append(binding.get("model_echoed")
                                            or (binding.get("record") or {}).get("model") or "?")
        rows.setdefault("ok / error", []).append(
            f"{env.get('ok')} / {(env.get('error') or {}).get('code') or '-'}")
        rows.setdefault("Latency (s)", []).append(str((env.get("timing") or {}).get("latency_s", "?")))
        rows.setdefault("Abstained", []).append(str(payload.get("abstained")))
        rows.setdefault("Entries", []).append(str(len(payload.get("entries") or [])))
        rows.setdefault("Downloads", []).append(str(len(payload.get("downloads") or [])))
        rows.setdefault("Problems (errors / warnings)", []).append(
            f"{len(problems)} ({sum(p.get('severity') == 'error' for p in problems)} / "
            f"{sum(p.get('severity') != 'error' for p in problems)})")
    checks = sorted({p.get("check") for ps in per_run_problems for p in ps})
    for c in checks:
        rows[f"  `{c}`"] = [str(sum(p.get("check") == c for p in ps)) for ps in per_run_problems]

    lines += ["## Summary" + (" (problems rechecked with the current Cog)" if do_recheck else ""),
              "", header, rule]
    lines += [f"| {k} | " + " | ".join(v) + " |" for k, v in rows.items()]

    closers = closed_by(bundle)
    placements = [with_closers(placement(env.get("payload") or {}), closers) for _, env in runs]
    lines += ["", "## How each run treated each source", "", header, rule]
    disagree = 0
    for s in bundle["sources"]:
        sid = s["id"]
        cells = ["; ".join(p.get(sid, [])) or "—" for p in placements]
        kinds = {kind_of(p.get(sid, [])) for p in placements}
        disagree += len(kinds) > 1
        mark = " ⚠" if len(kinds) > 1 else ""
        lines.append(f"| {sid}{mark} | " + " | ".join(cells) + " |")
    lines += ["", f"{disagree} of {len(bundle['sources'])} sources were placed differently "
                  "across runs (⚠)."]

    if key:
        lines += ["", "## Against the answer key", "", header, rule]
        scored = [sid for sid in key if any(s["id"] == sid for s in bundle["sources"])]
        hits = [sum(kind_of(p.get(sid, [])) == key[sid] for sid in scored) for p in placements]
        lines.append("| Sources placed as the key expects | "
                     + " | ".join(f"{h}/{len(scored)}" for h in hits) + " |")
        for sid in scored:
            got = [kind_of(p.get(sid, [])) for p in placements]
            if any(g != key[sid] for g in got):
                lines.append(f"| {sid} (key: {key[sid]}) | " + " | ".join(
                    g if g == key[sid] else f"**{g}**" for g in got) + " |")

    for (name, _), problems in zip(runs, per_run_problems):
        lines += ["", f"## Problems: {name}", ""]
        lines += [f"- {p.get('severity')} `{p.get('check')}`: {p.get('detail')}"
                  for p in problems] or ["- none"]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="+", help="envelope v1 result files")
    ap.add_argument("--bundle", required=True, help="the input bundle every run used")
    ap.add_argument("--names", help="comma-separated column names (default: file stems)")
    ap.add_argument("--recheck", action="store_true",
                    help="re-run the Cog's current contract checks on each payload")
    ap.add_argument("--answer-key", help='JSON {"source-id": "entry"|"excluded"|"gap"}')
    ap.add_argument("--out", help="write Markdown here (default: stdout)")
    args = ap.parse_args()

    names = args.names.split(",") if args.names else [Path(r).stem for r in args.runs]
    if len(names) != len(args.runs):
        ap.error("--names must name every run")
    bundle = load(args.bundle)
    runs = list(zip(names, (load(r) for r in args.runs)))
    key = load(args.answer_key) if args.answer_key else None
    text = report(bundle, runs, args.recheck, key)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
