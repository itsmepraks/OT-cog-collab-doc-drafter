---
type: cog [0.1]
name: cog-sonnet-gateway
description: Model Cog (deployment descriptor). Deployment descriptor for anthropic/claude-sonnet-4.6 (intelligence-hub gateway (OpenRouter-backed)), served over an OpenAI-compatible API. Carries the pinnable identity of the deployment; credentials and (where install-time) the address are installation facts.
version: "0.1.0"
license: BSD-3-Clause
publisher: OpenTeams
manifest: cog.yaml
manifest_schema: openteams/cog-manifest [0.1]
---

# Sonnet Gateway

Deployment descriptor for **anthropic/claude-sonnet-4.6** (intelligence-hub gateway (OpenRouter-backed)), served
over an OpenAI-compatible API. Created by cog-smith's `generate-descriptors` —
this is how a hosting environment publishes a model offering as an
ordinary, resolvable satisfier of `model-endpoint/openai-compatible`.

## Binding

```bash
# from a consumer context Cog:
pixi run resolve -- --satisfier ../cog-sonnet-gateway --endpoint <URL>
pixi run check -- --deep     # proves the route and verifies model identity
```

The consumer's binding record captures which model cog served which run —
that is where metering, quota, and audit attribution attach.

## What this package deliberately is NOT

It carries no weights, no runtime, no harness, and **no credentials**
(`api_key_env` names the environment variable a deployment expects — the
value is supplied by the environment, never by a package). Locality is
`cloud`: consumer Cogs whose manifests demand a stricter locality
will refuse to bind to it, by design.
