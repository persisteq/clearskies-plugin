#!/usr/bin/env python3
"""Install or refresh privacy-safe clearskies context for Claude and Codex."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any


SCHEMA_VERSION = 2
CONTEXT_METADATA_SCHEMA_VERSION = 2
SOURCE = "clearskies-mcp"
STANDARD_OBJECTS = {"account", "contact", "deal", "employee"}
BEGIN_MARKER = "<!-- clearskies-context:begin -->"
END_MARKER = "<!-- clearskies-context:end -->"

TOP_LEVEL_KEYS = {"schemaVersion", "generatedAt", "source", "schemaFingerprint", "objects"}
LEGACY_TOP_LEVEL_KEYS = {"schemaVersion", "generatedAt", "source", "objects"}
OBJECT_KEYS = {"objectType", "label", "kind", "fields"}
FIELD_KEYS = {
    "id",
    "fieldId",
    "name",
    "source",
    "label",
    "dataType",
    "validFilters",
    "enumValues",
    "referenceToObj",
    "editable",
}


class SnapshotError(ValueError):
    pass


def plugin_version() -> str:
    plugin_root = Path(__file__).resolve().parents[3]
    manifests = [
        plugin_root / ".codex-plugin" / "plugin.json",
        plugin_root / ".claude-plugin" / "plugin.json",
    ]
    versions: dict[str, str] = {}
    for manifest in manifests:
        if not manifest.is_file():
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read plugin manifest {manifest}: {exc}") from exc
        version = data.get("version") if isinstance(data, dict) else None
        if not isinstance(version, str) or not version.strip():
            raise ValueError(f"plugin manifest {manifest} has no valid version")
        versions[str(manifest)] = version.strip()

    if not versions:
        raise FileNotFoundError("no clearskies plugin manifest was found")
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        details = ", ".join(f"{path}={version}" for path, version in versions.items())
        raise ValueError(f"clearskies plugin manifest versions do not match: {details}")
    return unique_versions.pop()


def _schema_fingerprint(value: Any, path: str, *, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    fingerprint = _string(value, path)
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", fingerprint):
        raise SnapshotError(f"{path} must use the format sha256:<64 lowercase hex characters>")
    return fingerprint


def context_status(home: Path, live_schema_fingerprint: str | None = None) -> dict[str, Any]:
    current_version = plugin_version()
    if live_schema_fingerprint is not None:
        live_schema_fingerprint = _schema_fingerprint(
            live_schema_fingerprint, "live schema fingerprint"
        )
    metadata_path = home / ".clearskies" / "context-metadata.json"
    result: dict[str, Any] = {
        "status": "missing",
        "pluginVersion": current_version,
        "cachedPluginVersion": None,
        "cachedSchemaFingerprint": None,
        "liveSchemaFingerprint": live_schema_fingerprint,
        "fingerprintCompared": live_schema_fingerprint is not None,
        "contextMetadata": str(metadata_path),
    }
    if not metadata_path.is_file():
        return result

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        result["status"] = "invalid"
        result["error"] = f"could not read context metadata: {exc}"
        return result

    if not isinstance(metadata, dict):
        result["status"] = "invalid"
        result["error"] = "context metadata must be a JSON object"
        return result
    cached_version = metadata.get("pluginVersion")
    result["cachedPluginVersion"] = cached_version if isinstance(cached_version, str) else None
    cached_fingerprint = metadata.get("schemaFingerprint")
    try:
        cached_fingerprint = _schema_fingerprint(
            cached_fingerprint, "context metadata schemaFingerprint", nullable=True
        )
    except SnapshotError as exc:
        result["status"] = "invalid"
        result["error"] = str(exc)
        return result
    result["cachedSchemaFingerprint"] = cached_fingerprint
    if (
        metadata.get("schemaVersion") != CONTEXT_METADATA_SCHEMA_VERSION
        or "schemaFingerprint" not in metadata
        or not isinstance(cached_version, str)
        or not cached_version.strip()
    ):
        result["status"] = "invalid"
        result["error"] = "context metadata has an unsupported schema or plugin version"
        return result

    result["cachedPluginVersion"] = cached_version.strip()
    if cached_version.strip() != current_version:
        result["status"] = "stale"
        result["staleReason"] = "plugin-version"
    elif live_schema_fingerprint is not None and cached_fingerprint is None:
        result["status"] = "stale"
        result["staleReason"] = "missing-schema-fingerprint"
    elif live_schema_fingerprint is not None and cached_fingerprint != live_schema_fingerprint:
        result["status"] = "stale"
        result["staleReason"] = "schema-fingerprint"
    else:
        result["status"] = "current"
    return result


def _exact_keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = sorted(set(value) - allowed)
    missing = sorted(allowed - set(value))
    if unknown:
        raise SnapshotError(f"{path} contains unsupported keys: {', '.join(unknown)}")
    if missing:
        raise SnapshotError(f"{path} is missing keys: {', '.join(missing)}")


def _string(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotError(f"{path} must be a non-empty string")
    return value.strip()


def _timestamp(value: Any) -> str:
    raw = _string(value, "generatedAt")
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError("generatedAt must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None:
        raise SnapshotError("generatedAt must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_snapshot(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SnapshotError("snapshot must be a JSON object")
    _exact_keys(raw, TOP_LEVEL_KEYS, "snapshot")

    if raw["schemaVersion"] != SCHEMA_VERSION:
        raise SnapshotError(f"schemaVersion must be {SCHEMA_VERSION}")
    if raw["source"] != SOURCE:
        raise SnapshotError(f"source must be {SOURCE!r}")
    schema_fingerprint = _schema_fingerprint(
        raw["schemaFingerprint"], "schemaFingerprint", nullable=True
    )
    if not isinstance(raw["objects"], list):
        raise SnapshotError("objects must be an array")

    objects: list[dict[str, Any]] = []
    seen_objects: set[str] = set()
    for object_index, object_raw in enumerate(raw["objects"]):
        object_path = f"objects[{object_index}]"
        if not isinstance(object_raw, dict):
            raise SnapshotError(f"{object_path} must be an object")
        _exact_keys(object_raw, OBJECT_KEYS, object_path)

        object_type = _string(object_raw["objectType"], f"{object_path}.objectType")
        if object_type in seen_objects:
            raise SnapshotError(f"duplicate objectType: {object_type}")
        seen_objects.add(object_type)

        expected_kind = "standard" if object_type in STANDARD_OBJECTS else "custom"
        if object_raw["kind"] != expected_kind:
            raise SnapshotError(f"{object_path}.kind must be {expected_kind!r}")
        if not isinstance(object_raw["fields"], list):
            raise SnapshotError(f"{object_path}.fields must be an array")

        fields: list[dict[str, Any]] = []
        seen_fields: set[str] = set()
        for field_index, field_raw in enumerate(object_raw["fields"]):
            field_path = f"{object_path}.fields[{field_index}]"
            if not isinstance(field_raw, dict):
                raise SnapshotError(f"{field_path} must be an object")
            _exact_keys(field_raw, FIELD_KEYS, field_path)

            canonical_id = _string(field_raw["id"], f"{field_path}.id")
            if canonical_id in seen_fields:
                raise SnapshotError(f"duplicate canonical field id for {object_type}: {canonical_id}")
            seen_fields.add(canonical_id)

            nullable_strings: dict[str, str | None] = {}
            for key in ("name", "source", "referenceToObj"):
                value = field_raw[key]
                if value is not None:
                    value = _string(value, f"{field_path}.{key}")
                nullable_strings[key] = value
            filters = field_raw["validFilters"]
            if not isinstance(filters, list) or any(not isinstance(item, str) or not item.strip() for item in filters):
                raise SnapshotError(f"{field_path}.validFilters must be an array of strings")
            enum_values = field_raw["enumValues"]
            if not isinstance(enum_values, list) or any(
                not isinstance(item, str) or not item.strip() for item in enum_values
            ):
                raise SnapshotError(f"{field_path}.enumValues must be an array of strings")
            editable = field_raw["editable"]
            if editable is not None and not isinstance(editable, bool):
                raise SnapshotError(f"{field_path}.editable must be a boolean or null")

            fields.append(
                {
                    "id": canonical_id,
                    "fieldId": _string(field_raw["fieldId"], f"{field_path}.fieldId"),
                    "name": nullable_strings["name"],
                    "source": nullable_strings["source"],
                    "label": _string(field_raw["label"], f"{field_path}.label"),
                    "dataType": _string(field_raw["dataType"], f"{field_path}.dataType"),
                    "validFilters": sorted({item.strip() for item in filters}),
                    "enumValues": sorted({item.strip() for item in enum_values}),
                    "referenceToObj": nullable_strings["referenceToObj"],
                    "editable": editable,
                }
            )

        fields.sort(key=lambda field: (field["label"].casefold(), field["id"]))
        objects.append(
            {
                "objectType": object_type,
                "label": _string(object_raw["label"], f"{object_path}.label"),
                "kind": expected_kind,
                "fields": fields,
            }
        )

    objects.sort(key=lambda item: item["objectType"])
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": _timestamp(raw["generatedAt"]),
        "source": SOURCE,
        "schemaFingerprint": schema_fingerprint,
        "objects": objects,
    }


def normalize_existing_snapshot(raw: Any, replacement_fingerprint: str | None) -> dict[str, Any]:
    """Normalize current snapshots and migrate the previous v1 shape for diffing."""
    if (
        isinstance(raw, dict)
        and raw.get("schemaVersion") == 1
        and set(raw) == LEGACY_TOP_LEVEL_KEYS
    ):
        raw = dict(raw)
        raw["schemaVersion"] = SCHEMA_VERSION
        raw["schemaFingerprint"] = replacement_fingerprint
    return normalize_snapshot(raw)


def _map_objects(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["objectType"]: item for item in snapshot["objects"]}


def diff_snapshots(old: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    old_objects = _map_objects(old) if old else {}
    new_objects = _map_objects(new)
    old_types = set(old_objects)
    new_types = set(new_objects)

    changed_objects = sorted(
        object_type
        for object_type in old_types & new_types
        if {key: old_objects[object_type][key] for key in ("label", "kind")}
        != {key: new_objects[object_type][key] for key in ("label", "kind")}
    )

    added_fields: list[str] = []
    removed_fields: list[str] = []
    changed_fields: list[str] = []
    for object_type in sorted(old_types | new_types):
        old_fields = {field["id"]: field for field in old_objects.get(object_type, {}).get("fields", [])}
        new_fields = {field["id"]: field for field in new_objects.get(object_type, {}).get("fields", [])}
        for field_id in sorted(set(new_fields) - set(old_fields)):
            added_fields.append(f"{object_type}.{field_id}")
        for field_id in sorted(set(old_fields) - set(new_fields)):
            removed_fields.append(f"{object_type}.{field_id}")
        for field_id in sorted(set(old_fields) & set(new_fields)):
            if old_fields[field_id] != new_fields[field_id]:
                changed_fields.append(f"{object_type}.{field_id}")

    return {
        "firstRun": old is None,
        "objects": {
            "added": sorted(new_types - old_types),
            "removed": sorted(old_types - new_types),
            "changed": changed_objects,
        },
        "fields": {
            "added": added_fields,
            "removed": removed_fields,
            "changed": changed_fields,
        },
    }


def _markdown(value: Any) -> str:
    if value is None:
        return "—"
    return str(value).replace("|", "\\|").replace("\n", " ")


def render_profile(snapshot: dict[str, Any]) -> str:
    field_count = sum(len(item["fields"]) for item in snapshot["objects"])
    lines = [
        "# clearskies CRM data profile",
        "",
        "> Managed by the clearskies plugin. Rerun `setup clearskies` after CRM synchronization changes.",
        "> This file contains schema metadata only; it does not contain CRM values, transcripts, or email bodies.",
        "",
        f"- Refreshed: `{snapshot['generatedAt']}`",
        f"- Objects: {len(snapshot['objects'])}",
        f"- Fields: {field_count}",
        "",
    ]

    if not snapshot["objects"]:
        lines.extend(["No synchronized CRM object definitions were returned.", ""])
        return "\n".join(lines)

    for item in snapshot["objects"]:
        lines.extend(
            [
                f"## {_markdown(item['label'])}",
                "",
                f"- Object type: `{_markdown(item['objectType'])}`",
                f"- Kind: `{item['kind']}`",
                "",
                "| Field | Query field ID | Canonical ID | API/source name | Source | Data type | Filters | Enum values | Reference | Editable |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for field in item["fields"]:
            filters = ", ".join(f"`{_markdown(value)}`" for value in field["validFilters"]) or "—"
            enum_values = ", ".join(f"`{_markdown(value)}`" for value in field["enumValues"]) or "—"
            lines.append(
                "| "
                + " | ".join(
                    [
                        _markdown(field["label"]),
                        f"`{_markdown(field['fieldId'])}`",
                        f"`{_markdown(field['id'])}`",
                        _markdown(field["name"]),
                        _markdown(field["source"]),
                        f"`{_markdown(field['dataType'])}`",
                        filters,
                        enum_values,
                        _markdown(field["referenceToObj"]),
                        _markdown(field["editable"]),
                    ]
                )
                + " |"
            )
        if not item["fields"]:
            lines.append("| _No fields returned_ | — | — | — | — | — | — | — | — | — |")
        lines.append("")
    return "\n".join(lines)


def _managed_content(existing: str, block: str) -> str:
    begin_count = existing.count(BEGIN_MARKER)
    end_count = existing.count(END_MARKER)
    if begin_count != end_count or begin_count > 1:
        raise ValueError("host instruction file has malformed clearskies managed markers")

    if begin_count == 1:
        pattern = re.compile(re.escape(BEGIN_MARKER) + r".*?" + re.escape(END_MARKER), re.DOTALL)
        return pattern.sub(block, existing, count=1)

    if not existing:
        return block + "\n"
    separator = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
    return existing + separator + block + "\n"


def _stage(path: Path, content: bytes) -> tuple[Path, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return temporary, mode


def transactional_write(contents: dict[Path, str]) -> None:
    originals = {path: (path.read_bytes() if path.exists() else None) for path in contents}
    modes = {path: (stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600) for path in contents}
    staged: dict[Path, Path] = {}
    replaced: list[Path] = []
    try:
        for path, content in contents.items():
            staged[path] = _stage(path, content.encode("utf-8"))[0]
        for path, temporary in staged.items():
            os.replace(temporary, path)
            replaced.append(path)
    except Exception:
        for path in reversed(replaced):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                rollback, _ = _stage(path, original)
                os.chmod(rollback, modes[path])
                os.replace(rollback, path)
        raise
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)


def install(snapshot_path: Path, home: Path, install_global_loaders: bool = False) -> dict[str, Any]:
    try:
        incoming = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"could not read snapshot: {exc}") from exc
    snapshot = normalize_snapshot(incoming)

    context_dir = home / ".clearskies"
    previous_context = context_status(home)
    current_plugin_version = previous_context["pluginVersion"]
    snapshot_target = context_dir / "schema-snapshot.json"
    old_snapshot: dict[str, Any] | None = None
    if snapshot_target.exists():
        try:
            old_snapshot = normalize_existing_snapshot(
                json.loads(snapshot_target.read_text(encoding="utf-8")),
                snapshot["schemaFingerprint"],
            )
        except (OSError, json.JSONDecodeError, SnapshotError) as exc:
            raise SnapshotError(f"existing schema snapshot is invalid; no files were changed: {exc}") from exc

    default_source = (
        Path(__file__).resolve().parents[2]
        / "use-clearskies-revenue-data"
        / "references"
        / "default-guidelines.md"
    )
    if not default_source.is_file():
        raise FileNotFoundError(f"bundled default guidelines not found: {default_source}")
    default_guidelines = default_source.read_text(encoding="utf-8")
    profile = render_profile(snapshot)
    normalized_json = json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n"
    context_metadata = (
        json.dumps(
            {
                "schemaVersion": CONTEXT_METADATA_SCHEMA_VERSION,
                "pluginVersion": current_plugin_version,
                "generatedAt": snapshot["generatedAt"],
                "schemaFingerprint": snapshot["schemaFingerprint"],
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n"
    )

    contents = {
        context_dir / "context-metadata.json": context_metadata,
        context_dir / "default-guidelines.md": default_guidelines,
        context_dir / "data-profile.md": profile,
        snapshot_target: normalized_json,
    }
    claude_path = home / ".claude" / "CLAUDE.md"
    codex_path = home / ".codex" / "AGENTS.md"
    if install_global_loaders:
        claude_existing = claude_path.read_text(encoding="utf-8") if claude_path.exists() else ""
        codex_existing = codex_path.read_text(encoding="utf-8") if codex_path.exists() else ""
        claude_block = "\n".join(
            [
                BEGIN_MARKER,
                "# clearskies context (managed by the clearskies plugin)",
                "@~/.clearskies/default-guidelines.md",
                "@~/.clearskies/data-profile.md",
                END_MARKER,
            ]
        )
        codex_block = "\n".join(
            [
                BEGIN_MARKER,
                "## clearskies context (managed by the clearskies plugin)",
                "Before using clearskies tools, read `~/.clearskies/default-guidelines.md` and `~/.clearskies/data-profile.md`.",
                END_MARKER,
            ]
        )
        contents[claude_path] = _managed_content(claude_existing, claude_block)
        contents[codex_path] = _managed_content(codex_existing, codex_block)

    transactional_write(contents)

    result = diff_snapshots(old_snapshot, snapshot)
    files = {
        "contextMetadata": str(context_dir / "context-metadata.json"),
        "defaultGuidelines": str(context_dir / "default-guidelines.md"),
        "dataProfile": str(context_dir / "data-profile.md"),
        "schemaSnapshot": str(snapshot_target),
    }
    if install_global_loaders:
        files["claudeLoader"] = str(claude_path)
        files["codexLoader"] = str(codex_path)
    result["files"] = files
    result["context"] = {
        "status": "current",
        "pluginVersion": current_plugin_version,
        "previousPluginVersion": previous_context["cachedPluginVersion"],
        "versionChanged": previous_context["cachedPluginVersion"] != current_plugin_version,
        "schemaFingerprint": snapshot["schemaFingerprint"],
    }
    result["globalLoadersInstalled"] = install_global_loaders
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--snapshot-file", type=Path, help="Privacy-safe schema snapshot JSON")
    mode.add_argument("--check", action="store_true", help="Check cached plugin and schema freshness")
    parser.add_argument(
        "--schema-fingerprint",
        help="Live schemaStatus.fingerprint from object_definitions_list (use with --check)",
    )
    parser.add_argument(
        "--home",
        type=Path,
        default=Path.home(),
        help="Override the target home directory (primarily for isolated tests)",
    )
    parser.add_argument(
        "--install-global-loaders",
        action="store_true",
        help="Opt in to managed loader blocks in ~/.claude/CLAUDE.md and ~/.codex/AGENTS.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.check:
            print(
                json.dumps(
                    context_status(args.home.expanduser(), args.schema_fingerprint),
                    indent=2,
                    ensure_ascii=False,
                )
            )
            return 0
        if args.schema_fingerprint is not None:
            raise ValueError("--schema-fingerprint may only be used with --check")
        if args.snapshot_file is None:
            raise ValueError("--snapshot-file is required unless --check is used")
        result = install(
            args.snapshot_file.expanduser(),
            args.home.expanduser(),
            install_global_loaders=args.install_global_loaders,
        )
    except Exception as exc:
        print(f"setup-clearskies: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
