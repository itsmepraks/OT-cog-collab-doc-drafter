# Work contract: Collab Docs Drafter v0.1

Owner: Tife (work contract and harness). Draft for team review; nothing here
is final until Prakriti and Ebenezer agree. Answers the twelve questions in
cog-smith's BUILDING_COGS.md, section 6.

1. **Purpose.** Produce one thing: a release-notes draft for one Collab
   Desktop release, in which every claim points to the evidence behind it.

2. **User.** The person writing the release notes (today, Prakriti). They
   review the draft, fix the wording, decide the open questions and publish.
   Collab users read the final notes, never the raw draft.

3. **Supported work.** One release, identified by two tags: the previous
   release and this one (for example 0.7.1 → 0.7.2). Evidence is the merged
   pull requests that brought commits into that range, the issues they close,
   commits without a pull request, and the GitHub release record.

4. **Unsupported work.** Updating existing doc pages, summaries, roadmaps,
   more than one release at a time, and collecting evidence. The Cog never
   calls GitHub. It does not publish, edit repositories, change release
   metadata or approve wording. It does not use anything outside the bundle.

5. **Input.** A JSON bundle (`context/input-schema.json`): the release
   identity (product, repository, both tags, target commit, channel) and a
   list of sources, each with an id, kind, URL and text.
   `tools/collect_evidence.py` builds it from GitHub for a tag range. We use
   tags, not a branch: the Frame is right that a moving branch or a list of
   merged PRs does not show what shipped.

6. **Output.** Structured JSON (`context/output-schema.json`), so it can be
   checked by code and not just read: release facts, a short intro, one entry
   per user outcome (with category, body, the claims behind it and a review
   marker), download filenames, every excluded source with its reason, and
   gaps for the reviewer. `tools/render_notes.py` turns it into a Markdown
   page shaped like the published notes, plus a reviewer appendix.

7. **Grounding.** Every claim cites source ids and quotes one of them word for
   word. Code checks that each quote really appears in a cited source, that
   every cited id exists, that the version and channel match the bundle, that
   the date and download filenames appear in the release record, and that
   every source was either used, excluded or raised as a gap.

8. **Abstention.** Abstain only when the evidence cannot say what changed for
   users (for example, commits titled "wip" and "fix"). If every change is
   clearly internal, return a draft with no entries that says so. That is an
   answer, not an abstention. Unsupported or conflicting claims are left out
   and listed as gaps, while the rest of the draft continues.

9. **Requirements.** An OpenAI-compatible model endpoint. Default: the
   Collab-hosted Qwen3.5-35B on the Intelligence Hub (`customer-vpc`).
   Alternative: the Hub's Sonnet gateway (`cloud`). Locality is `any` for now.
   Small local models are not expected to do this task well.

10. **Prohibitions.** Never send external messages, modify source data,
    publish release notes or change release metadata. The Cog has no tools,
    so it has no means to. Text inside sources is treated as evidence, never
    as instructions.

11. **Evaluation.** Model-free tests (44 in the Cog, 9 for the tools) cover
    every contract check. Live fixtures cover a happy path (a synthetic 1.3.0
    release), abstention (thin evidence), an adversarial case (instructions
    planted in a PR, on a release candidate) and a boundary case (internal
    changes only). The real test is 0.7.2, compared by hand with Prakriti's
    published notes. Its evidence comes from a private repo, so it stays out
    of Git.

12. **Done.** For 0.7.2: every user-facing change in Prakriti's notes appears,
    nothing internal is presented as a user change, there are no grounding
    errors, the gaps are ones she agrees are real, and she says it saved her
    time.
