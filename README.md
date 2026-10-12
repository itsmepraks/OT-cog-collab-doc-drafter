Helps teams keep Collab documentation current as the product changes. It reviews product updates, GitHub issues, pull requests, release details, and existing documentation. It then drafts page updates, release notes, and summaries with links to the original sources. If information is missing or conflicting, it flags the gap instead of guessing.

Version 0.1 does one part of that: it drafts release notes for one Collab Desktop release from the evidence between two tags.

## What is here

| Path | What it is |
|---|---|
| [cog-collab-docs-drafter/](cog-collab-docs-drafter/) | The Cog, built with [cogcloud-ai/cog-smith](https://github.com/cogcloud-ai/cog-smith). Start with its [COG.md](cog-collab-docs-drafter/COG.md). |
| [cog-collab-docs-drafter/frames/](cog-collab-docs-drafter/frames/) | The Collab Release Documentation Quality Frame the Cog follows. |
| [tools/collect_evidence.py](tools/collect_evidence.py) | Builds the evidence bundle for a tag range from GitHub. Runs outside the Cog. |
| [tools/render_notes.py](tools/render_notes.py) | Turns the Cog's JSON result into a Markdown draft plus a reviewer appendix. |
| [docs/work-contract.md](docs/work-contract.md) | What the Cog takes in, gives back, and must never do. |
| [docs/spec-findings.md](docs/spec-findings.md) | What broke and where the spec was unclear, for Trent. |

## Quick start

```bash
cd cog-collab-docs-drafter
pixi install
pixi run test                                   # no model needed
```

The Cog only binds to models on your own machine: there is no Intelligence
Hub endpoint yet, and private release evidence must not go to an external
provider until the team approves one. To run it live, clone
[cogcloud-ai/cog-qwen](https://github.com/cogcloud-ai/cog-qwen) into this
repository's root (it is gitignored) and follow "Using it" in
[COG.md](cog-collab-docs-drafter/COG.md). Then:

```bash
cd cog-collab-docs-drafter
pixi run resolve -- --timeout 900 && pixi run check -- --deep
pixi run ask -- --bundle examples/sample-bundle.json > ../result.json
cd .. && python tools/render_notes.py result.json \
    --bundle cog-collab-docs-drafter/examples/sample-bundle.json --out draft.md
```

Always check the Cog with cogcloud-ai/cog-smith (`pixi run check --
../OT-cog-collab-doc-drafter/cog-collab-docs-drafter --tests` from a clone of
it). The older openteams-ai/cog-smith reports machinery-hash errors.

To draft a real release (needs `gh` with access to the product repository):

```bash
python tools/collect_evidence.py --previous 0.7.1 --target 0.7.2 \
    --out cog-collab-docs-drafter/evals/private/collab-0.7.2.bundle.json
```

`evals/private/` is gitignored. This repository is public and the product
repository is private, so real evidence bundles must not be committed.

Tests for the tools: `python -m unittest discover -s tools -p "test_*.py"`.
