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
CODEX_MANIFEST = ROOT / ".codex-plugin" / "plugin.json"
CLAUDE_MANIFEST = ROOT / ".claude-plugin" / "plugin.json"


def snapshot() -> dict:
    return {
        "schemaVersion": 2,
        "generatedAt": "2026-07-14T20:00:00Z",
        "source": "clearskies-mcp",
        "schemaFingerprint": "sha256:" + "a" * 64,
        "objects": [
            {
                "objectType": "account",
                "label": "Account",
                "kind": "standard",
                "fields": [
                    {
                        "id": "019f-field-definition",
                        "fieldId": "salesforce.Name",
                        "label": "Account Name",
                        "name": "Name",
                        "source": "salesforce",
                        "dataType": "string",
                        "validFilters": ["equal", "contains"],
                        "enumValues": ["Customer", "Prospect"],
                        "referenceToObj": None,
                        "editable": True,
                    }
                ],
            }
        ],
    }


class InstallContextTests(unittest.TestCase):
    def run_installer(
        self, home: Path, data: dict, *, install_global_loaders: bool = False
    ) -> subprocess.CompletedProcess[str]:
        snapshot_path = home / "input.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(data), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--home", str(home), "--snapshot-file", str(snapshot_path)]
        if install_global_loaders:
            command.append("--install-global-loaders")
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

    def run_check(
        self, home: Path, schema_fingerprint: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, str(SCRIPT), "--home", str(home), "--check"]
        if schema_fingerprint is not None:
            command.extend(["--schema-fingerprint", schema_fingerprint])
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_first_run_creates_context_directory_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)

            result = self.run_installer(home, snapshot())

            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertTrue(summary["firstRun"])
            self.assertEqual(
                set(summary["files"]),
                {
                    "contextMetadata",
                    "defaultGuidelines",
                    "dataProfile",
                    "dataProfileDirectory",
                    "schemaSnapshot",
                },
            )
            metadata = json.loads(
                (home / ".clearskies" / "context-metadata.json").read_text(encoding="utf-8")
            )
            current_version = json.loads(CODEX_MANIFEST.read_text(encoding="utf-8"))["version"]
            self.assertEqual(metadata["pluginVersion"], current_version)
            self.assertEqual(metadata["schemaFingerprint"], snapshot()["schemaFingerprint"])
            self.assertEqual(summary["context"]["pluginVersion"], current_version)
            self.assertEqual(
                summary["context"]["schemaFingerprint"], snapshot()["schemaFingerprint"]
            )
            self.assertTrue(summary["context"]["versionChanged"])
            self.assertTrue((home / ".clearskies" / "schema-snapshot.json").is_file())
            self.assertTrue((home / ".clearskies" / "data-profile.md").is_file())
            object_profiles = list((home / ".clearskies" / "data-profile").glob("object-*.md"))
            self.assertEqual(len(object_profiles), 1)
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((home / ".codex").exists())

    def test_default_run_does_not_touch_existing_global_instructions(self) -> None:
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
            index = (home / ".clearskies" / "data-profile.md").read_text(encoding="utf-8")
            self.assertIn("Keep reads small", index)
            self.assertIn("prefer live `schema_search`", index)
            self.assertIn("Account", index)
            self.assertNotIn("Account Name", index)
            profiles = list((home / ".clearskies" / "data-profile").glob("object-*.md"))
            self.assertEqual(len(profiles), 1)
            profile = profiles[0].read_text(encoding="utf-8")
            self.assertIn("fallback file", profile)
            self.assertIn("Account Name", profile)
            self.assertIn("salesforce.Name", profile)
            self.assertIn("Customer", profile)
            self.assertNotIn("Canonical ID", profile)
            self.assertNotIn("validFilters", profile)
            self.assertEqual(summary["globalLoadersInstalled"], False)
            self.assertEqual(
                (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"), "# Existing Claude rule\n"
            )
            self.assertEqual(
                (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"), "# Existing Codex rule\n"
            )

    def test_rerun_replaces_context_and_reports_schema_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            initial = snapshot()
            initial["objects"][0]["fields"].append(
                {
                    "id": "legacy-field",
                    "fieldId": "salesforce.Legacy__c",
                    "label": "Legacy Field",
                    "name": "Legacy__c",
                    "source": "salesforce",
                    "dataType": "string",
                    "validFilters": [],
                    "enumValues": [],
                    "referenceToObj": None,
                    "editable": False,
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
            self.assertEqual(summary["fields"]["changed"], ["account.019f-field-definition"])
            self.assertEqual(summary["fields"]["removed"], ["account.legacy-field"])
            self.assertFalse(summary["context"]["versionChanged"])
            profile_dir = home / ".clearskies" / "data-profile"
            profile_names = {path.name for path in profile_dir.glob("object-*.md")}
            self.assertEqual(len(profile_names), 2)
            self.assertTrue(any("custom-project" in name for name in profile_names))
            self.assertFalse(any("legacy-object" in name for name in profile_names))

    def test_refresh_migrates_previous_v1_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            context_dir = home / ".clearskies"
            context_dir.mkdir(parents=True)
            legacy = snapshot()
            legacy["schemaVersion"] = 1
            legacy.pop("schemaFingerprint")
            (context_dir / "schema-snapshot.json").write_text(
                json.dumps(legacy), encoding="utf-8"
            )
            current_version = json.loads(CODEX_MANIFEST.read_text(encoding="utf-8"))["version"]
            (context_dir / "context-metadata.json").write_text(
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "pluginVersion": current_version,
                        "generatedAt": legacy["generatedAt"],
                    }
                ),
                encoding="utf-8",
            )

            refreshed = self.run_installer(home, snapshot())

            self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
            summary = json.loads(refreshed.stdout)
            self.assertFalse(summary["firstRun"])
            migrated_snapshot = json.loads(
                (context_dir / "schema-snapshot.json").read_text(encoding="utf-8")
            )
            self.assertEqual(migrated_snapshot["schemaVersion"], 2)
            self.assertEqual(
                migrated_snapshot["schemaFingerprint"], snapshot()["schemaFingerprint"]
            )

    def test_check_reports_missing_current_stale_and_invalid_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)

            missing = self.run_check(home)
            self.assertEqual(missing.returncode, 0, missing.stderr)
            self.assertEqual(json.loads(missing.stdout)["status"], "missing")
            self.assertFalse((home / ".clearskies").exists())

            installed = self.run_installer(home, snapshot())
            self.assertEqual(installed.returncode, 0, installed.stderr)
            current = self.run_check(home)
            self.assertEqual(current.returncode, 0, current.stderr)
            self.assertEqual(json.loads(current.stdout)["status"], "current")

            metadata_path = home / ".clearskies" / "context-metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["pluginVersion"] = "0.0.0"
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            stale = self.run_check(home)
            self.assertEqual(stale.returncode, 0, stale.stderr)
            self.assertEqual(json.loads(stale.stdout)["status"], "stale")

            metadata_path.write_text("not json", encoding="utf-8")
            invalid = self.run_check(home)
            self.assertEqual(invalid.returncode, 0, invalid.stderr)
            self.assertEqual(json.loads(invalid.stdout)["status"], "invalid")

    def test_check_compares_live_schema_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            cached_fingerprint = snapshot()["schemaFingerprint"]
            installed = self.run_installer(home, snapshot())
            self.assertEqual(installed.returncode, 0, installed.stderr)

            matching = self.run_check(home, cached_fingerprint)
            matching_status = json.loads(matching.stdout)
            self.assertEqual(matching_status["status"], "current")
            self.assertTrue(matching_status["fingerprintCompared"])

            changed_fingerprint = "sha256:" + "b" * 64
            changed = self.run_check(home, changed_fingerprint)
            changed_status = json.loads(changed.stdout)
            self.assertEqual(changed_status["status"], "stale")
            self.assertEqual(changed_status["staleReason"], "schema-fingerprint")
            self.assertEqual(changed_status["cachedSchemaFingerprint"], cached_fingerprint)
            self.assertEqual(changed_status["liveSchemaFingerprint"], changed_fingerprint)

    def test_check_treats_missing_cached_fingerprint_as_stale_when_live_value_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            installed = self.run_installer(home, snapshot())
            self.assertEqual(installed.returncode, 0, installed.stderr)

            metadata_path = home / ".clearskies" / "context-metadata.json"
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata["schemaFingerprint"] = None
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

            checked = self.run_check(home, snapshot()["schemaFingerprint"])
            status = json.loads(checked.stdout)
            self.assertEqual(status["status"], "stale")
            self.assertEqual(status["staleReason"], "missing-schema-fingerprint")

    def test_invalid_fingerprint_is_rejected_without_replacing_context(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            installed = self.run_installer(home, snapshot())
            self.assertEqual(installed.returncode, 0, installed.stderr)
            profile_path = home / ".clearskies" / "data-profile.md"
            original_profile = profile_path.read_text(encoding="utf-8")

            invalid = copy.deepcopy(snapshot())
            invalid["schemaFingerprint"] = "not-a-fingerprint"
            rejected = self.run_installer(home, invalid)

            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("sha256:<64 lowercase hex characters>", rejected.stderr)
            self.assertEqual(profile_path.read_text(encoding="utf-8"), original_profile)

    def test_large_schema_emits_small_index_and_bounded_object_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            large = snapshot()
            large["objects"] = []
            object_types = ["account", "contact", "deal", "employee"] + [
                f"Custom_Object_{index}__c" for index in range(8)
            ]
            for object_index, object_type in enumerate(object_types):
                fields = []
                for field_index in range(81):
                    fields.append(
                        {
                            "id": f"field-{object_index}-{field_index}",
                            "fieldId": f"salesforce.Field_{object_index}_{field_index}__c",
                            "label": f"Field {object_index} {field_index}",
                            "name": f"Field_{object_index}_{field_index}__c",
                            "source": "salesforce",
                            "dataType": "string",
                            "validFilters": ["equal", "contains", "isEmpty", "isNotEmpty"],
                            "enumValues": [f"Value {enum_index}" for enum_index in range(30)],
                            "referenceToObj": None,
                            "editable": True,
                        }
                    )
                large["objects"].append(
                    {
                        "objectType": object_type,
                        "label": "Opportunity" if object_type == "deal" else object_type,
                        "kind": "standard" if object_type in {"account", "contact", "deal", "employee"} else "custom",
                        "fields": fields,
                    }
                )

            installed = self.run_installer(home, large)

            self.assertEqual(installed.returncode, 0, installed.stderr)
            context_dir = home / ".clearskies"
            index_path = context_dir / "data-profile.md"
            profiles = list((context_dir / "data-profile").glob("object-*.md"))
            self.assertEqual(len(large["objects"]), 12)
            self.assertEqual(sum(len(item["fields"]) for item in large["objects"]), 972)
            self.assertLess(index_path.stat().st_size, 16_000)
            self.assertEqual(len(profiles), 12)
            self.assertLess(max(path.stat().st_size for path in profiles), 64_000)
            self.assertTrue(all("(+18 more)" in path.read_text(encoding="utf-8") for path in profiles))

    def test_host_plugin_manifest_versions_match(self) -> None:
        codex_version = json.loads(CODEX_MANIFEST.read_text(encoding="utf-8"))["version"]
        claude_version = json.loads(CLAUDE_MANIFEST.read_text(encoding="utf-8"))["version"]
        self.assertEqual(codex_version, claude_version)

    def test_global_loaders_require_opt_in_and_are_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()
            (home / ".claude" / "CLAUDE.md").write_text("# Existing Claude rule\n", encoding="utf-8")
            (home / ".codex" / "AGENTS.md").write_text("# Existing Codex rule\n", encoding="utf-8")

            first = self.run_installer(home, snapshot(), install_global_loaders=True)
            second = self.run_installer(home, snapshot(), install_global_loaders=True)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            summary = json.loads(second.stdout)
            self.assertTrue(summary["globalLoadersInstalled"])
            claude = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
            codex = (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("Existing Claude rule", claude)
            self.assertIn("Existing Codex rule", codex)
            self.assertNotIn("~/.clearskies/data-profile.md", claude)
            self.assertNotIn("~/.clearskies/data-profile.md", codex)
            self.assertNotIn("@~/.clearskies/data-profile.md", claude)
            self.assertIn("live `schema_search`", claude)
            self.assertIn("live `schema_search`", codex)
            self.assertIn("Do not load the saved schema profile", claude)
            self.assertIn("Do not load the saved schema profile", codex)
            self.assertEqual(claude.count("clearskies-context:begin"), 1)
            self.assertEqual(codex.count("clearskies-context:begin"), 1)

    def test_invalid_or_sensitive_snapshot_leaves_existing_context_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            first = self.run_installer(home, snapshot())
            self.assertEqual(first.returncode, 0, first.stderr)
            profile_path = home / ".clearskies" / "data-profile.md"
            original_profile = profile_path.read_text(encoding="utf-8")

            invalid = copy.deepcopy(snapshot())
            invalid["objects"][0]["fields"][0]["sampleValue"] = "Sensitive customer value"
            second = self.run_installer(home, invalid)

            self.assertNotEqual(second.returncode, 0)
            self.assertIn("unsupported keys", second.stderr)
            self.assertEqual(profile_path.read_text(encoding="utf-8"), original_profile)


if __name__ == "__main__":
    unittest.main()
