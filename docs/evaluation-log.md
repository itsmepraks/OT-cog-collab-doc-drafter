# Evaluation log

Live runs of the Cog against real release evidence. The evidence, raw
results and drafts are private (apollo-desktop is a private repository), so
they live only in the gitignored `cog-collab-docs-drafter/evals/private/`.
This log records counts, failure classes and decisions, never evidence text.

Compare runs with:

```bash
pixi run --manifest-path cog-collab-docs-drafter/pixi.toml python tools/compare_runs.py \
    --bundle cog-collab-docs-drafter/evals/private/collab-0.7.2.bundle.json \
    --recheck  run-a.result.json run-b.result.json --names a,b
```

`--recheck` scores every run with the Cog's current contract checks, so runs
made before a check existed stay comparable.

## Run 1 — 0.7.1 → 0.7.2, qwen3:14b (Prakriti, 2026-11-02)

**Setup.** main @cca04df; local Ollama `qwen3:14b`, 32,768-token context,
`--response-format json_object`, timeout 1800 s. Bundle: 11 pull requests,
5 issues, the release record (17 sources).

**Result.** `ok: true`, no transport or runtime error, 218 s, 4 entries.
13 problems as run: 1 schema, 6 grounding, 6 coverage. Not publishable; a
useful baseline. The quality gate caught the unsafe parts it was built to
catch.

**What went wrong, by class** (checked by hand against the evidence):

| Class | Count | What happened |
|---|---|---|
| Quote stitched with `[...]` | 3 | The model joined separate passages inside one quote. |
| Quote off by one character | 2 | Correct span, but ended with `.` where the source continues with `:` or `,`. |
| Label not in evidence | 1 | A menu path that no source writes out. It matched an example in our own `system.md`, which we have removed. |
| Exclusion reason misspelled | 1 | `test_only` for `tests_only`. |
| Fabricated gaps | 2 | Both gaps claimed testing on platforms the cited pull requests never mention. The wording came from the worked example's gap. **Not caught at the time.** |
| Unaccounted sources | 6 | 5 issues closed by pull requests the run did account for, and 1 pull request (#745) with the issue it closes. |
| Missing download | 1 | The Linux `.asc` signature. **Not caught at the time.** |
| Judgment calls | 2 | #746 (History response protection) excluded as internal; the published notes include it. #743 (a release-pipeline cleanup fix) written up as a user-facing installer fix. Both wait on the answer key. |

**Changes made in response** (branch `tife/harden-after-0.7.2-run`):

- New checks: `platform` (an entry may not name a platform its sources never
  mention; a gap that does is warned), `example-copy` (wording shared with the
  worked example but absent from the evidence), `downloads` (every asset in
  the release record must be listed), and `grounding-hint` (why a quote
  failed: an ellipsis, or where it stops matching).
- Coverage now counts an issue as accounted for when a pull request that
  closes it is. The collector records this as `closed_by`, and the model sees
  "Closed by: pr-N".
- Prompt: no ellipses in quotes; prefer a short continuous span; no menu paths
  the sources do not write out; no platforms the sources do not name; do not
  reuse the worked example's wording in gaps; list every asset; check every
  source once before finishing.

**Rechecked with the new checks** (same saved output, no new model call):
20 problems, 7 errors and 13 warnings. Both fabricated gaps and the missing
`.asc` are now reported. Unaccounted sources fall from 6 to 2, both genuine
(#745 and the issue it closes). Every failed quote has a hint.

**Still open:** the answer key (#743, #746, #748), whether a repair pass
belongs in the Cog or in an Op, and model-to-model variability (needs more
runs).
