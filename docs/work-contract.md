# Work contract: Collab Docs Drafter v0.1

Answers the twelve questions in cog-smith's BUILDING_COGS.md, section 6.
Merged from Tife's first draft and Prakriti's review (Slack, October 2026),
which Ebenezer agreed with. Where a rule is enforced by code, the location is
given in brackets.

1. **Purpose.** One artifact: an evidence-linked release-note draft for one
   Collab Desktop release. This is the first practical step toward the larger
   aim of keeping Collab documentation current as the product changes.

2. **Primary users.** The Collab documentation maintainer, who reviews the
   draft, resolves its questions, corrects its wording and decides whether it
   meets the quality bar. Release owners may also review release status and
   unresolved product questions.

3. **Supported work.** One release, bounded by a previous tag and a target
   tag (for example 0.7.1 → 0.7.2). For the commits in that range the Cog
   reviews: merged pull requests associated with them, issues those pull
   requests close, commits without a merged pull request, and the GitHub
   release record with its asset names and publication metadata. It
   identifies user-facing additions, improvements, fixes, limitations and
   required user actions.

4. **Unsupported work.** Rewriting existing documentation pages; identifying or
   updating affected guides; general product summaries or roadmaps; several
   releases at once; collecting evidence from GitHub (a host step does that:
   `tools/collect_evidence.py`); editing repositories; publishing release
   notes; changing release metadata; approving final wording; using anything
   outside the supplied evidence. Page updates stay in the long-term vision,
   not in v1.

5. **Required input.** A structured evidence bundle
   [`context/input-schema.json`]: product and repository identity, previous
   tag, target tag, target commit when available, release channel, the
   sources listed in 3, and collection warnings such as truncated sources.
   Tags define the release boundary; a moving branch or an unverified list of
   merged pull requests does not prove what shipped. Missing or equal tags,
   duplicate source ids, or no pull request or commit refuse the run; a
   missing target commit is a warning [`check_input`].

6. **Exact output.** A structured draft [`context/output-schema.json`]:
   release version, channel and date; a short introduction; one entry per
   user-visible outcome with category, title, user-facing explanation and
   human-review marker; the claims behind each entry with source ids and
   quotations; download and integrity filenames; every excluded source and
   why; missing evidence, conflicts and reviewer questions; abstention status
   and reason. `tools/render_notes.py` turns it into a Markdown draft plus a
   separate evidence appendix. It stays a draft until a person approves it.

7. **Evidence and grounding.** Every substantive claim names its sources,
   quotes at least one of them word for word, keeps qualifications (platform,
   scope, limits, prerequisites) and claims no more than the evidence shows.
   Deterministic checks [`check_output`] verify that: every cited source
   exists; every quotation appears in a cited source; release identity
   matches the bundle; the release date and download filenames come from the
   release record; every **bold** UI label or `code` name in a title, body or
   intro appears in a source that text cites; and every source is cited,
   excluded or raised as a gap. These checks establish traceability, not
   truth. A reviewer still decides whether the evidence supports the wording.

8. **Abstention and conflicts.** Abstain when the evidence is too weak to say
   what changed for users. If every change is clearly internal, return a
   valid draft with no user-facing entries that says so; that is not an
   abstention. If only some evidence is missing or contradictory, continue
   with the independently supported entries and put the rest in gaps. Never
   invent content to fill a section.

9. **Model and runtime.** A model that follows detailed instructions, treats
   sources as untrusted data, produces valid JSON, preserves verbatim quotes
   and fits the bundle. There is no Intelligence Hub endpoint yet (Trent,
   October 5): testing runs on team machines. Private Apollo evidence must not
   go to an external provider until the organization approves that boundary,
   so the manifest only allows `local` bindings. The default is Qwen3-4B
   through cogcloud-ai/cog-qwen; its 8k context fits the synthetic fixtures
   but not a real release, which needs a local server with a 32k context.
   Credentials, model bindings and private evidence are never committed.

10. **Prohibited actions.** Never invent facts, sources or quotations; follow
    instructions inside source material; reveal secrets, private identities,
    internal hosts or sensitive logs; use evidence outside the bundle; modify
    source data; edit repositories; send external messages; publish release
    notes; change release metadata; decide whether a release ships; or
    present generated wording as approved. Installing or running the Cog
    grants it no tools, credentials, network access or authority.

11. **Evaluation.** Model-free tests cover every contract check, including the
    grounding-failure and wrong-metadata-source cases. Live fixtures, all
    synthetic and public: happy path, thin evidence (abstain), prompt
    injection (ignore it, report `suspicious_input`), internal-only release,
    and conflicting evidence (keep the narrower supported scope, report the
    conflict, cancel out a merge and its revert). The real evaluation is the
    private 0.7.2 bundle, reviewed against an answer key Prakriti prepares.
    The published 0.7.2 notes are reference material, not automatic ground
    truth; exceptions such as #743 ("Windows package checks") are judged
    against the Frame.

12. **Definition of done.** The Frame is packaged and referenced by the Cog.
    The work contract, schemas, examples and implementation agree. The Cog
    passes the team's chosen cog-smith (cogcloud-ai/cog-smith). Model-free and
    live synthetic evaluations pass. Private evidence and credentials stay out
    of Git. The Cog processes the approved 0.7.2 evidence: expected
    user-facing changes appear, internal-only changes do not, every public
    claim is traceable, missing or conflicting information is reported, and
    the output is clearly marked for human review. Prakriti confirms that
    correcting the draft is meaningfully more useful than writing the notes
    from scratch.
