---
type: cog [0.1]
name: cog-collab-docs-drafter
description: Drafts Collab release notes from supplied release evidence, with a source for every claim and explicit gaps.
version: "0.1.0"
license: Apache-2.0
manifest: cog.yaml
manifest_schema: openteams/cog-manifest [0.1]
---

# Collab Docs Drafter

## Purpose

Given a Collab release and its merged pull requests, draft release notes for
Collab users. Every factual statement links to the source it came from. When
evidence is missing, unclear or contradictory, the Cog reports the gap for
human review instead of guessing. The result is a draft; people approve it.

## Supported work

- Drafting release notes for one Collab release from supplied evidence.
- Linking each claim to a source ID from the input.
- Listing gaps, conflicts and questions for the reviewer.

TODO (work contract): exact accepted inputs, output format, grounding rule.

## Unsupported work

- Updating existing documentation pages or writing summaries (future work).
- Editing repositories, publishing notes, or changing release metadata.
- Using any information not included in the supplied evidence.

These boundaries are enforced by the prohibitions in cog.yaml.

## Quality standards

Editorial and evidence standards come from the Collab Release Documentation
Quality Frame. TODO: link the Frame file.

## Using it

TODO: add run instructions once the package runs.
