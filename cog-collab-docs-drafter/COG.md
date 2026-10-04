---
type: cog [0.1]
name: cog-collab-docs-drafter
description: "Context Cog. Drafts Collab release notes from supplied release evidence, links every claim to its source, and flags missing or conflicting information. Depends on a Cog providing an OpenAI-compatible model endpoint."
version: "0.1.0"
license: Apache-2.0
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-manifest [0.1]
---

# Collab Docs Drafter

## Purpose

Given one Collab release, bounded by its previous tag and its own tag, and the
evidence for what changed between them, draft release notes for Collab users.
Every factual statement cites the sources it came from and quotes one of them
word for word. When evidence is missing, unclear or contradictory, the Cog
reports the gap for human review instead of guessing. The result is a draft;
people approve it.

## Supported work

- Drafting release notes for one Collab release from a release evidence
  bundle: merged pull requests, the issues they close, commits without a pull
  request, and the GitHub release record.
- Deciding which changes are user-facing, and listing every other source as
  excluded with a reason (CI, tests, release tooling, refactors, docs-site
  changes, duplicates and ports).
- Linking each claim to source IDs from the input, with a verbatim quote.
- Reporting the release identity, date and download filenames only as the
  release record states them.
- Listing gaps, conflicts, suspicious input and questions for the reviewer.

## Unsupported work

- Updating existing documentation pages or writing summaries (future work).
- Collecting evidence. The Cog never calls GitHub; a host step does, for
  example tools/collect_evidence.py in this repository.
- Editing repositories, publishing notes, or changing release metadata.
- Approving wording or deciding whether a release ships.
- Using any information not included in the supplied evidence.

These boundaries are enforced by the prohibitions in cog.yaml. The Cog holds
no tools, so it has no way to act outside its answer.

## Inputs

A JSON bundle matching [context/input-schema.json](context/input-schema.json):

- `release`: product, repository, `previous_tag`, `target_tag`, optional
  `target_commit`, and `channel` (stable, prerelease or unknown). The tag
  range is the release boundary; a branch name or a list of merged pull
  requests does not establish what shipped.
- `sources`: evidence items, each with an `id` (`pr-755`, `issue-751`,
  `commit-477c830`, `release-0.7.2`), a `kind`, a `url` and the `text`.
- `notes`: caveats about the bundle, such as truncated sources.

The bundle is refused before any model call if the tags are missing or equal,
source IDs repeat, or no pull request or commit is supplied.

## Output

Envelope v1 with a payload matching
[context/output-schema.json](context/output-schema.json):

- `release`: version, previous version, channel, date and the sources for them.
- `intro`: one to three sentences, with sources.
- `entries`: one per user outcome, with a `category` (added, improved, fixed,
  known_limitation, action_required), a user-facing `body`, the `claims` that
  back it, and a `review` marker.
- `downloads`: package, checksum and signature filenames from the release record.
- `excluded`: every source left out, with the reason.
- `gaps`: missing evidence, conflicts, suspicious input, and owner decisions.
- `abstained` and `abstain_reason`.

## Grounding and abstention

- Every claim cites source IDs and carries an `evidence_quote` that must be a
  verbatim span of a cited source (whitespace may differ, nothing else).
- The release date and download filenames must appear in a cited source.
- Every source must be cited, excluded or named in a gap. A source the draft
  ignores is reported as a coverage warning.
- The Cog abstains only when the evidence cannot tell what changed for users.
  A release whose changes are all internal gets a draft with no entries, not
  an abstention.

These checks run inside the Cog and appear in the envelope's `problems`. They
are the Cog's self-report, not Guards. `ok: true` can carry problems; a Gate
or a reviewer decides.

## Quality standards

Editorial and evidence standards come from the Collab Release Documentation
Quality Frame, maintained by Prakriti Bista. Until manifests can list Frames,
[context/system.md](context/system.md) carries its rules.

## Limitations

- Quality depends on the bound model. Small models struggle with verbatim
  quoting and with deciding what is user-facing.
- A verbatim quote shows that the evidence contains the words, not that the
  claim is right. A person still reviews every entry.
- The Cog cannot see whether a package was distributed, a page deployed, or a
  change tested on every platform. It reports those as gaps.
- Sources longer than the collector's limit are truncated, and the bundle
  notes say so.

## Using it

```bash
pixi install
pixi run test               # model-free deterministic suite

# Bind an Intelligence Hub model (writes model.json, which is gitignored)
export COLLAB_API_KEY=...   # the key stays in the environment, never in a file
pixi run resolve -- --endpoint https://YOUR-COLLAB-HOST/v1
# or the Hub gateway:
#   export HUB_GATEWAY_API_KEY=...
#   pixi run resolve -- --satisfier cog-sonnet-gateway --endpoint https://YOUR-GATEWAY/v1
pixi run check -- --deep    # prove the binding: endpoint + model identity

pixi run ask -- --bundle examples/sample-bundle.json
pixi run eval               # fixtures in evals/ against the bound model
pixi run serve              # web API on http://127.0.0.1:8120/ask
```

To draft a real release, build its bundle from the repository root with
`python tools/collect_evidence.py --previous 0.7.1 --target 0.7.2 --out <file>`,
then pass that file to `ask`. Bundles from private repositories stay out of
Git; see evals/collab-0.7.2.fixture.yaml.

Results are **envelope v1** (see cog-smith/ENVELOPE.md): fixed `payload` key,
structured `problems`, complete `binding` identity in every result.

## Where the machinery came from

Everything in `src/` except `task_logic.py` is shared cog-smith machinery
derived from cog-forge @7fe8aca (engineering-gates PASS). Do not edit it here;
`smith check` verifies the copies. This Cog's identity lives in `cog.yaml`,
`context/`, and `src/task_logic.py`.
