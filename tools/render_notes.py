#!/usr/bin/env python3
"""Render a cog-collab-docs-drafter result as Markdown for review.

    pixi run ask -- --bundle bundle.json > result.json
    python tools/render_notes.py result.json --bundle bundle.json --out draft.md

Takes an envelope v1 result (or a bare payload) and writes one Markdown file
with two parts:

  1. the public draft, shaped like the pages under
     apollo-desktop-docs/src/content/docs/releases/; and
  2. a reviewer appendix: every claim with its quote and source links, the
     excluded sources, the gaps, and the Cog's own `problems`.

This is presentation only. It adds no facts: everything comes from the
payload, and source links come from the bundle. Standard library only.
"""
import argparse
import json
import sys

PLATFORMS_NOTE = "Package and integrity filenames:"


def _q(text):
    """Quote a YAML scalar safely."""
    return json.dumps(str(text), ensure_ascii=False)


def _links(ids, urls):
    return ", ".join(f"[{i}]({urls[i]})" if urls.get(i) else i for i in ids or [])


def render_public(payload, product):
    rel = payload.get("release") or {}
    version = rel.get("version", "?")
    entries = payload.get("entries") or []
    out = ["---",
           f"title: {_q(f'{product} {version}')}",
           f"description: {_q((payload.get('intro') or {}).get('text', ''))}",
           "release:",
           f"  version: {_q(version)}",
           f"  date: {rel.get('release_date') or 'null'}",
           "  highlights:"]
    out += [f"    - {_q(e.get('title', ''))}" for e in entries] or ["    []"]
    out += ["draft: true", "---", ""]

    if rel.get("channel") == "prerelease":
        out += ["> **Release candidate.** This is not a stable release.", ""]
    when = f" · Released {rel['release_date']}" if rel.get("release_date") else ""
    out += [f"**Version {version}{when}**", "",
            (payload.get("intro") or {}).get("text", ""), ""]

    for e in entries:
        marker = " *(needs owner review)*" if e.get("review") == "needs_owner_review" else ""
        out += [f"## {e.get('title', '')}{marker}", "", e.get("body", "").strip(), ""]

    downloads = payload.get("downloads") or []
    if downloads:
        out += ["## Downloads", "", PLATFORMS_NOTE, ""]
        current = None
        for d in downloads:
            if d.get("platform") != current:
                current = d.get("platform")
                out.append(f"- **{current}**")
            out.append(f"  - `{d.get('filename')}`")
        out.append("")
    return out


def render_review(envelope, payload, urls):
    out = ["---", "", "# Reviewer appendix (not for publication)", ""]
    if envelope is not None:
        binding = envelope.get("binding") or {}
        model = binding.get("model_echoed") or (binding.get("record") or {}).get("model")
        out += [f"- Cog: {(envelope.get('cog') or {}).get('id')} "
                f"{(envelope.get('cog') or {}).get('version')}",
                f"- Model: {model or 'unknown'}",
                f"- ok: {envelope.get('ok')}", ""]
        problems = envelope.get("problems") or []
        out += ["## Problems the Cog reported", ""]
        out += [f"- **{p.get('severity', 'error')}** `{p.get('check')}`: {p.get('detail')}"
                for p in problems] or ["- none"]
        out.append("")

    if payload.get("abstained"):
        out += ["## Abstained", "", payload.get("abstain_reason") or "(no reason given)", ""]

    out += ["## Claims and evidence", ""]
    for e in payload.get("entries") or []:
        out += [f"### {e.get('title')} ({e.get('category')}, {e.get('review')})", ""]
        for c in e.get("claims") or []:
            out += [f"- {c.get('text')}",
                    f"  - Sources: {_links(c.get('source_ids'), urls)}",
                    f"  - Quote: \"{c.get('evidence_quote')}\""]
        out.append("")
    rel = payload.get("release") or {}
    out += [f"Release facts from: {_links(rel.get('source_ids'), urls) or 'none'}", ""]

    out += ["## Excluded sources", ""]
    out += [f"- {_links(x.get('source_ids'), urls)} — {x.get('reason')}: {x.get('note')}"
            for x in payload.get("excluded") or []] or ["- none"]
    out += ["", "## Gaps and questions", ""]
    out += [f"- **{g.get('kind')}** ({_links(g.get('source_ids'), urls) or 'no sources'}): {g.get('detail')}"
            for g in payload.get("gaps") or []] or ["- none"]
    out.append("")
    return out


def render(result, bundle=None):
    envelope = result if "payload" in result and "envelope" in result else None
    payload = envelope.get("payload") if envelope else result
    if payload is None:
        err = (envelope or {}).get("error") or {}
        return f"# No draft\n\nThe Cog returned no payload: {err.get('code')}: {err.get('detail')}\n"
    bundle = bundle or {}
    urls = {s["id"]: s.get("url") for s in bundle.get("sources") or []}
    product = (bundle.get("release") or {}).get("product", "Collab Desktop")
    return "\n".join(render_public(payload, product) + render_review(envelope, payload, urls))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("result", help="envelope v1 JSON from `pixi run ask`, or a bare payload")
    ap.add_argument("--bundle", help="the input bundle, for source links and product name")
    ap.add_argument("--out", help="write here (default: stdout)")
    args = ap.parse_args()
    with open(args.result, encoding="utf-8") as fh:
        result = json.load(fh)
    bundle = None
    if args.bundle:
        with open(args.bundle, encoding="utf-8") as fh:
            bundle = json.load(fh)
    text = render(result, bundle)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
