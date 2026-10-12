# What broke and where the spec was unclear

A running list for Trent, as he asked. Add to it as we go. Each item says what
we saw, where, and what we did about it.

Checked against: cogcloud-ai/cog-smith main @c700f66 (2026-10-09),
openteams-ai/cog-spec main @06ad55f (2026-09-03), openteams-ai/frame-spec main
@796fe39 (2026-09-07), cogcloud-ai/cog-qwen main (2026-09-24).

## Open questions

1. **How should a Cog list its Frames?** `frames` is in the manifest, but
   neither CogSpec nor cog-smith defines its shape, and cog-smith does not
   check it. No Cog in cogcloud-ai sets one. The nebi-cog-package example pins
   Frames as package dependencies instead. Our proposal for now:
   `frames = ["frames/collab-release-documentation-quality.frame.md"]`, a
   path relative to the Cog root, with the Frame packaged in the Cog. A test
   fails if `context/system.md` and the Frame name different versions. Is
   this acceptable until the real shape exists?

2. **Can a private evidence bundle be an evaluation fixture?** Our real test
   (0.7.2) comes from a private repository and our repository is public.
   `evaluation.fixtures` has no notion of private or local-only fixtures, so
   the 0.7.2 fixture is run by path and not declared.

3. **How does a Cog say how much context it needs?** cog-qwen serves Qwen3-4B
   with `--ctx-size 8192`. A real release bundle for us is about 16,000
   tokens, so binding succeeds, `check --deep` passes, and the first real
   `ask` would fail. The nebi-cog-package example has
   `inference.min-context`, but the cog-smith profile has no such field and
   descriptors do not state their context window, so resolution cannot catch
   the mismatch.

4. **Locality is declared, not verified.** We set `locality = "local"` because
   private evidence must not reach an external provider. `pixi run use
   openrouter` is refused, as it should be. But `pixi run use --endpoint
   https://api.example.com/v1 --locality local` is accepted: the binder labels
   the endpoint. A loopback check for `local` would close the obvious case.

## Resolved

5. **Where does the manifest live?** *Resolved.* Trent (October 5): both
   forms are valid, but OpenTeams systems use `pixi.toml` because of Nebi.
   cogcloud-ai/cog-smith writes `[tool.cog]` in `pixi.toml` by default since
   machinery 0.3.0, and `smith migrate` converts a `cog.yaml` package. We
   migrated.

6. **Any input problem refused the run, including warnings.** *Fixed upstream*
   in cogcloud-ai/cog-smith (5b9c17c, 2026-10-08): warnings now travel in
   `problems` and only errors refuse. We restored our "target commit missing"
   warning.

7. **The default satisfier assumed the workshop layout.** *Changed upstream:*
   new Cogs default to `../cog-qwen`, the public local provider. We use that
   and gitignore a `cog-qwen/` clone at our repository root.

## Things that surprised us

8. **Two cog-smiths, and the old one gives no sign it is old.** We first built
   from openteams-ai/cog-smith (private), whose main has not changed since
   2026-08-23. The current builder is cogcloud-ai/cog-smith (public), which
   Trent mentioned in the October 5 sync. Ebenezer checked our package with
   the newer one and got six machinery-hash errors. Nothing in the old
   repository points to the new one. A note or archive flag on the old
   repository would have saved a round trip.

9. **A machinery change without a version.** The 2026-10-08 input-severity
   fix changed the context-cog `cog_core.py`, and so its hash, but
   MACHINERY.md still ends at context-cog 0.4.3. Two packages can both say
   "0.4.3" while one fails `smith check` against the other. Every hash change
   should be a version.

10. **`smith migrate` leaves `python = ">=3.10"`.** After migration the
    machinery reads `[tool.cog]` with `tomllib`, which needs Python 3.11, but
    migrate does not raise the floor in `[dependencies]`. We changed it by
    hand. Migrate also drops comments from the manifest it converts.

11. **A hand-written package passed `smith check`.** It passed the core and
    profile layers with two warnings. The runtime layer was skipped ("package
    carries no cog-smith machinery"), so the four missing `context/` files the
    manifest declared were never reported. A declared file that does not
    exist seems worth an error at the profile layer.

12. **Eval `grounded: true` fails on warnings too.** Any problem fails it,
    whatever its severity. Defensible, but not documented next to `severity`.

13. **Eval fixtures cannot check anything nested.** `min_entries` and
    `categories_*` look only at `entries`/`findings` and an entry's
    `category`, and `fields` (machinery 0.4.2) compares top-level values. Our
    conflicting-evidence and prompt-injection cases need "a gap of kind
    `conflicting_evidence` exists" or "no entry cites pr-720", which a fixture
    cannot say. A reviewer checks those by hand.

## Environment notes

- Pixi was not installed on one of our machines. cog-smith's commands also run
  as `python src/cogsmith_cli.py <command>` with `pyyaml` and `jsonschema`.
- One laptop (8 GB RAM, about 0.5 GB free) cannot run cog-qwen alongside an
  editor. Live evaluation needs a machine with roughly 4 GB free for the 4B
  model, more for the 32k-context model a real release needs.
