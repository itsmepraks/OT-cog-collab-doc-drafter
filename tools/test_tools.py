"""Model-free, network-free tests for the host-side tools.

    python -m unittest discover -s tools -p "test_*.py"
"""
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import collect_evidence as ce   # noqa: E402
import render_notes as rn       # noqa: E402

COG = HERE.parent / "cog-collab-docs-drafter"


def commit(sha, message, date="2026-09-01T00:00:00Z"):
    return {"sha": sha, "commit": {"message": message, "committer": {"date": date}}}


class TestCollector(unittest.TestCase):
    def test_commits_group_by_merged_pr_and_orphans_stay_commits(self):
        commits = [commit("a" * 40, "feat: x (#1)"), commit("b" * 40, "fix: y"),
                   commit("c" * 40, "test: z (#1)")]
        prs = {"a" * 40: [{"number": 1, "merged_at": "2026-09-01"}],
               "b" * 40: [{"number": 2, "merged_at": None}],   # open PR: not merged
               "c" * 40: [{"number": 1, "merged_at": "2026-09-01"}]}
        by_pr, orphans = ce.group_commits_by_pr(commits, prs.get)
        self.assertEqual(sorted(by_pr), [1])
        self.assertEqual(len(by_pr[1]), 2)
        self.assertEqual([c["sha"] for c in orphans], ["b" * 40])

    def test_truncate_marks_the_cut(self):
        text, cut = ce.truncate("x" * 50, 10)
        self.assertTrue(cut)
        self.assertIn("truncated by collector", text)
        self.assertEqual(ce.truncate("short", 10), ("short", False))

    def test_channel_comes_from_the_release_record(self):
        self.assertEqual(ce.channel_for(None), "unknown")
        self.assertEqual(ce.channel_for({"prerelease": True}), "prerelease")
        self.assertEqual(ce.channel_for({"prerelease": False}), "stable")

    def test_pr_source_lists_its_range_commits_and_no_author(self):
        pr = {"number": 755, "title": "feat(settings): add an on-demand update check",
              "url": "https://github.com/o/r/pull/755", "mergedAt": "2026-09-02T15:59:20Z",
              "baseRefName": "main", "labels": [], "body": "Closes #751.\n\nAdds **Check for updates**.",
              "author": {"login": "someone"}}
        src, cut = ce.pr_source(pr, [commit("fe6ff94" + "0" * 33, "feat(settings): add an on-demand update check (#755)")], 8000)
        self.assertFalse(cut)
        self.assertEqual(src["id"], "pr-755")
        self.assertIn("- fe6ff94 feat(settings)", src["text"])
        self.assertIn("Adds **Check for updates**.", src["text"])
        self.assertNotIn("someone", json.dumps(src))

    def test_release_source_lists_assets(self):
        rel = {"tag_name": "0.7.2", "name": "0.7.2", "published_at": "2026-09-02T20:02:16Z",
               "prerelease": False, "draft": False, "target_commitish": "main",
               "html_url": "https://github.com/o/r/releases/tag/0.7.2", "body": "",
               "assets": [{"name": "collab-desktop-macos.dmg"}]}
        src, _ = ce.release_source(rel, 8000)
        self.assertEqual(src["id"], "release-0.7.2")
        self.assertIn("Published: 2026-09-02T20:02:16Z", src["text"])
        self.assertIn("- collab-desktop-macos.dmg", src["text"])
        self.assertIn("(empty)", src["text"])


class TestRenderer(unittest.TestCase):
    def setUp(self):
        self.payload = json.loads((COG / "context" / "output-example.json").read_text())
        self.bundle = json.loads((COG / "tests" / "fixtures" / "worked-example-bundle.json").read_text())

    def test_public_draft_and_appendix(self):
        text = rn.render(self.payload, self.bundle)
        self.assertIn('title: "Collab Desktop 2.4.1"', text)
        self.assertIn("draft: true", text)
        self.assertIn("## Filter History by Frame", text)
        self.assertIn("`collab-desktop-macos.dmg`", text)
        self.assertIn("# Reviewer appendix (not for publication)", text)
        self.assertIn("[pr-102](https://github.com/example-org/collab-desktop-example/pull/102)", text)

    def test_prerelease_banner(self):
        self.payload["release"]["channel"] = "prerelease"
        self.assertIn("**Release candidate.**", rn.render(self.payload, self.bundle))

    def test_envelope_problems_are_shown(self):
        env = {"envelope": 1, "ok": True, "cog": {"id": "x", "version": "0"}, "binding": {},
               "payload": self.payload,
               "problems": [{"check": "coverage", "detail": "pr-1 unused", "severity": "warning"}]}
        self.assertIn("`coverage`: pr-1 unused", rn.render(env, self.bundle))

    def test_failed_envelope_says_so(self):
        env = {"envelope": 1, "ok": False, "payload": None,
               "error": {"code": "invalid-input", "detail": "release: required"}}
        self.assertIn("invalid-input", rn.render(env))


if __name__ == "__main__":
    unittest.main()
