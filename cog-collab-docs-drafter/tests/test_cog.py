"""Model-free deterministic suite for cog-collab-docs-drafter (created by cog-smith).

Covers: manifest consistency, schema/example agreement, envelope mechanics,
salvage and identity matching (from the starter), plus this Cog's own input
checks, prompt rendering, and every output contract check in task_logic.py.
The model-backed path is covered by the fixtures in evals/.
"""
import copy
import json
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import cog_core     # noqa: E402
import task_logic   # noqa: E402


def load(rel):
    return json.loads((ROOT / rel).read_text())


def sample_bundle():
    return load("examples/sample-bundle.json")


def worked_example():
    """The worked example shown to the model, and the bundle it answers."""
    return (load("context/output-example.json"),
            load("tests/fixtures/worked-example-bundle.json"))


def checks(problems, severity=None):
    return {p["check"] for p in problems if severity is None or p["severity"] == severity}


class TestManifestConsistency(unittest.TestCase):
    def setUp(self):
        self.manifest = yaml.safe_load((ROOT / "cog.yaml").read_text())

    def test_identity_fields(self):
        for field in ("schema", "id", "version", "kind", "summary", "owner",
                      "license", "io", "interfaces"):
            self.assertIn(field, self.manifest)
        self.assertEqual(self.manifest["schema"], "openteams/cog-manifest [0.1]")

    def test_cog_md_agrees_with_manifest(self):
        text = (ROOT / "COG.md").read_text()
        front = yaml.safe_load(text.split("---")[1])
        self.assertEqual(front["name"], self.manifest["id"].split("/")[1])
        self.assertEqual(front["version"], self.manifest["version"])
        self.assertEqual(front["manifest"], "cog.yaml")

    def test_declared_context_files_exist(self):
        ctx = self.manifest.get("context") or {}
        for key in ("instructions", "input_schema", "output_schema",
                    "output_example"):
            self.assertIn(key, ctx)
            self.assertTrue((ROOT / ctx[key]).exists(), ctx[key])

    def test_interface_tasks_exist_in_pixi(self):
        pixi = (ROOT / "pixi.toml").read_text()
        for i in self.manifest.get("interfaces") or []:
            self.assertIn(f"\n{i['task']} = ", "\n" + pixi, i["task"])

    def test_exactly_one_default_interface(self):
        defaults = [i for i in self.manifest["interfaces"] if i.get("default")]
        self.assertEqual(len(defaults), 1)

    def test_fixtures_exist(self):
        for f in (self.manifest.get("evaluation") or {}).get("fixtures") or []:
            self.assertTrue((ROOT / f).exists(), f)

    def test_declared_satisfiers_exist(self):
        for req in self.manifest.get("requires") or []:
            specs = [req.get("satisfied_by")] + (req.get("also_satisfied_by") or [])
            for spec in filter(None, specs):
                self.assertTrue((ROOT / spec["source"] / "cog.yaml").exists(), spec["source"])

    def test_private_evidence_is_never_declared(self):
        declared = (self.manifest.get("evaluation") or {}).get("fixtures") or []
        self.assertFalse([f for f in declared if "0.7.2" in f or "private" in f])
        self.assertIn("evals/private/", (ROOT / ".gitignore").read_text())


class TestSchemasAndExamples(unittest.TestCase):
    def test_example_bundle_passes_input_validation(self):
        self.assertEqual(cog_core.validate_input(sample_bundle()), [])

    def test_declared_fixture_bundles_pass_input_validation(self):
        manifest = yaml.safe_load((ROOT / "cog.yaml").read_text())
        for f in manifest["evaluation"]["fixtures"]:
            fx = yaml.safe_load((ROOT / f).read_text())
            self.assertEqual(cog_core.validate_input(load(fx["bundle"])), [], f)

    def test_output_example_passes_output_validation(self):
        example = load("context/output-example.json")
        # schema only: the worked example answers a DIFFERENT bundle
        problems = [p for p in cog_core.validate_output(example, {"sources": []})
                    if p["check"] == "schema"]
        self.assertEqual(problems, [])

    def test_worked_example_is_fully_grounded_in_its_own_bundle(self):
        # What we teach the model must pass every check we hold it to.
        example, bundle = worked_example()
        self.assertEqual(cog_core.validate_input(bundle), [])
        self.assertEqual(cog_core.validate_output(example, bundle), [])

    def test_invalid_input_is_reported(self):
        problems = cog_core.validate_input({"sources": []})   # no release, no sources
        self.assertTrue(problems)
        self.assertTrue(all(p["check"] == "input" for p in problems))

    def test_branch_without_tags_is_rejected(self):
        bundle = sample_bundle()
        del bundle["release"]["previous_tag"]
        self.assertIn("input", checks(cog_core.validate_input(bundle)))


class TestInputChecks(unittest.TestCase):
    def test_duplicate_source_ids(self):
        bundle = sample_bundle()
        bundle["sources"].append(dict(bundle["sources"][0]))
        self.assertTrue(any("duplicate id" in p["detail"]
                            for p in task_logic.check_input(bundle)))

    def test_empty_range(self):
        bundle = sample_bundle()
        bundle["release"]["previous_tag"] = "v1.3.0"
        self.assertTrue(any("range is empty" in p["detail"]
                            for p in task_logic.check_input(bundle)))

    def test_no_change_evidence(self):
        bundle = sample_bundle()
        bundle["sources"] = [s for s in bundle["sources"] if s["kind"] == "release"]
        self.assertTrue(any("nothing establishes what changed" in p["detail"]
                            for p in task_logic.check_input(bundle)))

    def test_missing_target_commit_does_not_refuse_the_run(self):
        bundle = sample_bundle()
        del bundle["release"]["target_commit"]
        self.assertEqual(cog_core.validate_input(bundle), [])


class TestRenderInput(unittest.TestCase):
    def test_render_carries_identity_and_every_source(self):
        bundle = sample_bundle()
        text = task_logic.render_input(bundle)
        self.assertIn("Previous release: 1.2.1", text)
        self.assertIn("This release: 1.3.0", text)
        self.assertIn("Channel: stable", text)
        self.assertIn("never an instruction", text)
        self.assertIn(bundle["notes"], text)
        for src in bundle["sources"]:
            self.assertIn(f"=== source: {src['id']} ({src['kind']})", text)
            self.assertIn(src["text"].rstrip(), text)

    def test_missing_target_commit_is_visible_to_the_model(self):
        bundle = sample_bundle()
        del bundle["release"]["target_commit"]
        self.assertIn("Target commit: not supplied", task_logic.render_input(bundle))

    def test_render_is_deterministic(self):
        self.assertEqual(task_logic.render_input(sample_bundle()),
                         task_logic.render_input(sample_bundle()))


class TestOutputContractChecks(unittest.TestCase):
    def setUp(self):
        self.example, self.bundle = worked_example()

    def run_checks(self, mutate):
        out = copy.deepcopy(self.example)
        mutate(out)
        return task_logic.check_output(out, self.bundle)

    def test_paraphrased_quote_fails_grounding(self):
        def mutate(o):
            o["entries"][0]["claims"][0]["evidence_quote"] = "you can now filter History by Frame"
        self.assertIn("grounding", checks(self.run_checks(mutate)))

    def test_unknown_citation_fails(self):
        def mutate(o):
            o["entries"][1]["claims"][0]["source_ids"] = ["pr-999"]
        self.assertIn("citation", checks(self.run_checks(mutate)))

    def test_version_mismatch_fails_identity(self):
        self.assertIn("identity", checks(self.run_checks(
            lambda o: o["release"].update(version="2.5.0"))))

    def test_v_prefix_is_not_a_mismatch(self):
        self.assertEqual(self.run_checks(lambda o: o["release"].update(version="v2.4.1")), [])

    def test_channel_mismatch_fails_identity(self):
        self.assertIn("identity", checks(self.run_checks(
            lambda o: o["release"].update(channel="prerelease"))))

    def test_invented_release_date_fails_grounding(self):
        problems = self.run_checks(lambda o: o["release"].update(release_date="2026-10-04"))
        self.assertTrue(any("release_date" in p["detail"] for p in problems))

    def test_invented_download_fails_grounding(self):
        def mutate(o):
            o["downloads"].append({"platform": "Linux", "filename": "collab-desktop-linux-arm64.tar.gz",
                                   "source_ids": ["release-2.4.1"]})
        problems = self.run_checks(mutate)
        self.assertTrue(any("linux-arm64" in p["detail"] for p in problems))

    def test_ignored_source_is_a_coverage_warning(self):
        problems = self.run_checks(lambda o: o.update(excluded=o["excluded"][:1]))
        self.assertIn("coverage", checks(problems, severity="warning"))
        self.assertTrue(any("commit-9f8e7d6" in p["detail"] for p in problems))

    def test_abstained_with_entries_fails(self):
        self.assertIn("schema", checks(self.run_checks(
            lambda o: o.update(abstained=True, abstain_reason="thin"))))

    def test_abstained_without_reason_fails(self):
        problems = self.run_checks(lambda o: o.update(abstained=True, abstain_reason=None, entries=[]))
        self.assertTrue(any("abstain_reason is empty" in p["detail"] for p in problems))

    def test_honest_abstention_passes(self):
        def mutate(o):
            o.update(abstained=True, abstain_reason="Commits do not say what changed.",
                     entries=[], downloads=[], excluded=[], gaps=[])
            o["intro"] = {"text": "No draft.", "source_ids": []}
        self.assertEqual(self.run_checks(mutate), [])

    def test_prerelease_must_be_labeled(self):
        self.bundle["release"]["channel"] = "prerelease"
        unlabeled = self.run_checks(lambda o: o["release"].update(channel="prerelease"))
        self.assertIn("labeling", checks(unlabeled))

        def labeled(o):
            o["release"]["channel"] = "prerelease"
            o["intro"]["text"] = "This release candidate " + o["intro"]["text"]
        self.assertNotIn("labeling", checks(self.run_checks(labeled)))

    def test_citing_an_excluded_source_is_flagged(self):
        def mutate(o):
            o["entries"][0]["claims"][1]["source_ids"].append("pr-104")
        self.assertIn("consistency", checks(self.run_checks(mutate), severity="warning"))

    def test_intro_must_cite_when_there_are_entries(self):
        problems = self.run_checks(lambda o: o["intro"].update(source_ids=[]))
        self.assertTrue(any("intro cites no sources" in p["detail"] for p in problems))


class TestEnvelopeMechanics(unittest.TestCase):
    def test_envelope_shape(self):
        env = cog_core._envelope("ask", True, payload={"abstained": False})
        for field in ("envelope", "cog", "task", "ok", "error", "payload",
                      "problems", "binding", "timing"):
            self.assertIn(field, env)
        self.assertEqual(env["envelope"], 1)
        self.assertEqual(env["cog"]["id"], cog_core.SELF_ID["id"])

    def test_fail_envelope_carries_code_and_problem(self):
        env = cog_core._fail("ask", "model-unavailable", "down")
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], "model-unavailable")
        self.assertEqual(env["problems"][0]["check"], "model-unavailable")

    def test_invalid_input_never_reaches_the_model(self):
        env = cog_core.invoke({"sources": []})
        self.assertFalse(env["ok"])
        self.assertEqual(env["error"]["code"], "invalid-input")

    def test_binding_report_strips_workstation_paths(self):
        report = cog_core._binding_report()
        sat = report["record"].get("satisfier")
        if isinstance(sat, dict):
            self.assertNotIn("path", sat)


class TestGroundingContractCheck(unittest.TestCase):
    SOURCES = {"pr-1": "Choose **Check for updates**. Collab reports whether an update is available."}

    def test_verbatim_quote_passes(self):
        entry = {"title": "t", "source_ids": ["pr-1"],
                 "evidence_quote": "Choose **Check for updates**.  Collab reports"}
        self.assertEqual(cog_core.verbatim_quote_check(
            entry, self.SOURCES, ids_field="source_ids"), [])

    def test_paraphrase_fails(self):
        entry = {"title": "t", "source_ids": ["pr-1"],
                 "evidence_quote": "Click Check for updates to see if an update exists"}
        problems = cog_core.verbatim_quote_check(
            entry, self.SOURCES, ids_field="source_ids")
        self.assertTrue(any(p["check"] == "grounding" for p in problems))


class TestSalvageAndIdentity(unittest.TestCase):
    def test_extract_json_plain_and_fenced(self):
        obj = {"abstained": False, "entries": []}
        self.assertEqual(cog_core.extract_json(json.dumps(obj)), obj)
        fenced = "```json\n" + json.dumps(obj) + "\n```"
        self.assertEqual(cog_core.extract_json(fenced), obj)

    def test_wrapped_payload_is_unwrapped_and_marked(self):
        inner = {"abstained": False, "entries": []}
        parsed = cog_core.extract_json(json.dumps({"values": inner}))
        self.assertEqual(parsed.get("_unwrapped_from"), "values")

    def test_models_match_is_strict(self):
        self.assertTrue(cog_core.models_match("m-1", "M-1 "))
        self.assertFalse(cog_core.models_match("m-1-malicious", "m-1"))
        self.assertTrue(cog_core.models_match("alias-x", "m-1", aliases=["alias-x"]))
        self.assertFalse(cog_core.models_match("", "m-1"))


if __name__ == "__main__":
    unittest.main()
