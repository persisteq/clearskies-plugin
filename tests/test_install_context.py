from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "setup-clearskies" / "scripts" / "install_context.py"


def snapshot() -> dict:
    return {
        "schemaVersion": 1,
        "generatedAt": "2026-07-14T20:00:00Z",
        "source": "clearskies-mcp",
        "objects": [
            {
                "objectType": "account",
                "label": "Account",
                "kind": "standard",
                "fields": [
                    {
                        "id": "account-name",
                        "label": "Account Name",
                        "name": "Name",
                        "dataType": "string",
                        "validFilters": ["equal", "contains"],
                    }
                ],
            }
        ],
    }


class InstallContextTests(unittest.TestCase):
    def run_installer(self, home: Path, data: dict) -> subprocess.CompletedProcess[str]:
        snapshot_path = home / "input.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(data), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--home", str(home), "--snapshot-file", str(snapshot_path)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_first_run_preserves_host_instructions_and_installs_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()
            (home / ".claude" / "CLAUDE.md").write_text("# Existing Claude rule\n", encoding="utf-8")
            (home / ".codex" / "AGENTS.md").write_text("# Existing Codex rule\n", encoding="utf-8")

            result = self.run_installer(home, snapshot())

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertTrue(summary["firstRun"])
            self.assertEqual(summary["objects"]["added"], ["account"])
            self.assertTrue((home / ".clearskies" / "default-guidelines.md").is_file())
            profile = (home / ".clearskies" / "tenant-profile.md").read_text(encoding="utf-8")
            self.assertIn("Account Name", profile)
            self.assertNotIn("record values", json.dumps(snapshot()))
            self.assertIn("Existing Claude rule", (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertIn("Existing Codex rule", (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"))

    def test_rerun_replaces_managed_blocks_and_reports_schema_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            initial = snapshot()
            initial["objects"][0]["fields"].append(
                {
                    "id": "legacy-field",
                    "label": "Legacy Field",
                    "name": "Legacy__c",
                    "dataType": "string",
                    "validFilters": [],
                }
            )
            initial["objects"].append(
                {"objectType": "legacy_object", "label": "Legacy Object", "kind": "custom", "fields": []}
            )
            first = self.run_installer(home, initial)
            self.assertEqual(first.returncode, 0, first.stderr)

            changed = copy.deepcopy(snapshot())
            changed["generatedAt"] = "2026-07-15T20:00:00Z"
            changed["objects"][0]["label"] = "Company"
            changed["objects"][0]["fields"][0]["label"] = "Company Name"
            changed["objects"].append(
                {"objectType": "custom_project", "label": "Project", "kind": "custom", "fields": []}
            )
            second = self.run_installer(home, changed)

            self.assertEqual(second.returncode, 0, second.stderr)
            summary = json.loads(second.stdout)
            self.assertFalse(summary["firstRun"])
            self.assertEqual(summary["objects"]["added"], ["custom_project"])
            self.assertEqual(summary["objects"]["removed"], ["legacy_object"])
            self.assertEqual(summary["objects"]["changed"], ["account"])
            self.assertEqual(summary["fields"]["changed"], ["account.account-name"])
            self.assertEqual(summary["fields"]["removed"], ["account.legacy-field"])
            self.assertEqual((home / ".claude" / "CLAUDE.md").read_text().count("clearskies-context:begin"), 1)
            self.assertEqual((home / ".codex" / "AGENTS.md").read_text().count("clearskies-context:begin"), 1)

    def test_invalid_or_sensitive_snapshot_leaves_existing_context_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            first = self.run_installer(home, snapshot())
            self.assertEqual(first.returncode, 0, first.stderr)
            profile_path = home / ".clearskies" / "tenant-profile.md"
            original_profile = profile_path.read_text(encoding="utf-8")

            invalid = copy.deepcopy(snapshot())
            invalid["objects"][0]["fields"][0]["sampleValue"] = "Sensitive customer value"
            second = self.run_installer(home, invalid)

            self.assertNotEqual(second.returncode, 0)
            self.assertIn("unsupported keys", second.stderr)
            self.assertEqual(profile_path.read_text(encoding="utf-8"), original_profile)


if __name__ == "__main__":
    unittest.main()
