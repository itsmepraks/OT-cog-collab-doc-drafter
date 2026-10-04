# What broke and where the spec was unclear

A running list for Trent, as he asked. Add to it as we go. Each item says what
we saw, where, and what we did about it.

Checked against: cog-smith main @1677cb7 (2026-08-23), cog-spec main @06ad55f
(2026-09-03), frame-spec main @796fe39 (2026-09-07).

## Open questions

1. **Where does the manifest live?** Trent told Ebenezer the manifest goes in
   `pixi.toml` by default. cog-smith's `new` still writes `cog.yaml` and points
   `COG.md` at it, and BUILDING_COGS.md describes `cog.yaml`. The only
   `pixi.toml` manifest is cog-spec's `examples/nebi-cog-package`, which says
   it is "illustrative only and is not part of the minimum v0.1 adopt-now
   spec". We kept what cog-smith generates. Which is current?

2. **How should a Cog list its Frames?** `frames: []` is in the manifest, but
   its shape is not defined. The nebi-cog-package example pins Frames as
   package dependencies instead. We left it empty and carry the Frame's rules
   in `context/system.md`.

3. **Can a private evidence bundle be an evaluation fixture?** Our real test
   case (0.7.2) is built from a private repository, but our repository is
   public. `evaluation.fixtures` has no notion of private or local-only
   fixtures, so the 0.7.2 fixture is run by path and not declared.

## Things that surprised us

4. **A hand-written package passed `smith check`.** We expected it to fail
   (that was the reason given for regenerating). It passed the core and
   profile layers with two warnings. The runtime layer was skipped with a
   warning ("package carries no cog-smith machinery"), so the four missing
   `context/` files the manifest declared were never reported. A declared
   file that does not exist seems worth an error at the profile layer.

5. **Any input problem refuses the run, including warnings.**
   `cog_core.invoke` refuses on any problem from `validate_input`, whatever
   its severity. A soft input warning (for example "target commit not
   supplied") cannot be expressed. We moved that case into the prompt so the
   model raises it as a gap. Either the docs should say so, or `invoke` should
   only refuse on errors.

6. **Eval `grounded: true` fails on warnings too.** The fixture check treats
   any problem as a failure. That is defensible, but it is not documented next
   to the `severity` field.

7. **Eval expectations assume `entries` or `findings`.** `min_entries` and
   `categories_*` only look at those keys and an entry's `category`. We named
   ours to fit. Other output shapes cannot use these checks.

8. **The default satisfier path assumes the workshop layout.** `new` defaults
   to `../cog-demo/cog-qwen3b`. Outside that layout `resolve` fails. We
   generated Intelligence Hub descriptors into `models/` and pointed at them.

9. **The Frame spec moved to v0.2.** Our Frame says `type: frame [0.1]`. The
   v0.2 validator still accepts it, but new Frames should say `frame [0.2]`.

## Environment notes

- Pixi was not installed on one of our machines. cog-smith's commands also run
  as `python src/cogsmith_cli.py <command>` with `pyyaml` and `jsonschema`
  installed, which helped while getting set up.
