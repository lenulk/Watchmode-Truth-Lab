"""Run via test_cycle.py --test artifact_checks to audit retained artifacts."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ArtifactChecks(unittest.TestCase):
    def test_evidence_json_and_matrix_summaries_are_consistent(self):
        count = 0
        for path in (ROOT / "evidence").rglob("*.json"):
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                data = json.loads(path.read_text(encoding="utf-8"))
                count += 1
                if path.name == "summary.json":
                    for entry in data:
                        target = path.parent / entry["file"]
                        self.assertTrue(target.is_file(), entry)
                        scenario = json.loads(target.read_text(encoding="utf-8"))
                        self.assertEqual(entry["status"], scenario.get("report", scenario)["status"])
                        if "assessment" in entry:
                            self.assertEqual(entry["assessment"], scenario["assessment"])
                elif "tests_run" in data:
                    self.assertTrue(path.with_suffix(".log").is_file())
                    self.assertEqual(data["status"], "fail" if data["failures"] or data["errors"] else "pass")
        self.assertGreater(count, 0)

    def test_document_local_links_resolve(self):
        documents = [ROOT / "README.md", *(ROOT / "docs").glob("*.md")]
        for document in documents:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(document=document.name, target=target):
                    path = (document.parent / target.split("#", 1)[0]).resolve()
                    self.assertTrue(path.is_relative_to(ROOT))
                    self.assertTrue(path.is_file(), str(path))

    def test_evidence_has_no_literal_user_home_paths(self):
        pattern = re.compile(r"(?:[A-Za-z]:[\\/]+Users[\\/]+|/home/)[A-Za-z0-9_.-]+", re.IGNORECASE)
        for path in (ROOT / "evidence").rglob("*"):
            if path.suffix not in {".json", ".log"}:
                continue
            with self.subTest(file=path.relative_to(ROOT).as_posix()):
                self.assertIsNone(pattern.search(path.read_text(encoding="utf-8")))
