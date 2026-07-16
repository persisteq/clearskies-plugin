---
name: setup-clearskies
description: Set up or refresh clearskies context for Claude and Codex by discovering every connected CRM object and field and generating privacy-safe data files under ~/.clearskies. Use after installing or updating the clearskies plugin, when cached context is missing or stale, when a user says "setup clearskies," or whenever CRM objects or synchronized fields have changed.
---

# Setup clearskies

Discover the complete current CRM schema and install shared, rerunnable context for Claude and Codex. Skills load this context only when clearskies work is requested, so setup does not add global context by default.

## Guardrails

- Read metadata only. Do not fetch CRM record values, event contents, transcripts, or email bodies.
- Complete all MCP discovery before invoking the installer. An authentication or discovery failure must leave the last valid files untouched.
- Ask for filesystem approval when the host requires it for writes under the user's home directory.
- Treat `~/.clearskies/context-metadata.json`, `default-guidelines.md`, `data-profile.md`, `data-profile/`, and `schema-snapshot.json` as plugin-managed paths.
- Do not modify `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md` by default.
- Install global loader blocks only when the user explicitly asks for always-on clearskies context and confirms the global edits. Preserve all content outside the plugin-owned marker blocks.

## Discover the schema

1. Call `object_definitions_list`. If the connector is unavailable or unauthenticated, stop and explain how to connect it.
2. Read `schemaStatus.fingerprint` from the response. Treat it as a version for the complete query-relevant CRM schema, not as record data or a timestamp:
   - Compare the full opaque value exactly; never parse, shorten, or recompute it.
   - Do not use `lastCheckedAt` to decide whether schema content changed. It records the latest successful schema refresh, while only the fingerprint represents content.
   - If the server omits `schemaStatus`, freshness is unknown. Continue with full discovery and store `null`; do not invent a fingerprint.
3. Before fetching every field, resolve the installer path below and, when both a live fingerprint and cached context exist, run `python3 <resolved-installer-path> --check --schema-fingerprint <live-fingerprint>`.
   - If the result is `current`, stop: the plugin version and query-relevant CRM schema both match the cache. Report `clearskies context is current`; do not call `object_get_fields_schema` or rewrite the cached files.
   - If the result is `missing`, `stale`, or `invalid`, continue with full discovery. A `staleReason` of `schema-fingerprint` means the connected schema changed; `plugin-version` means the installed guidance changed; `missing-schema-fingerprint` means the cache predates fingerprint tracking.
4. For every returned `objectType`, call `object_get_fields_schema`. Do not omit empty, custom, or unfamiliar objects.
5. Build one JSON snapshot using only this shape:

```json
{
  "schemaVersion": 2,
  "generatedAt": "2026-07-14T20:00:00Z",
  "source": "clearskies-mcp",
  "schemaFingerprint": "sha256:7682ed30b4bc4570062a8bd19e5688d9602d0a161995435e9fad82ad4341de9f",
  "objects": [
    {
      "objectType": "account",
      "label": "Account",
      "kind": "standard",
      "fields": [
        {
          "id": "019f-canonical-field-definition-id",
          "fieldId": "salesforce.Name",
          "name": "Name",
          "source": "salesforce",
          "label": "Account Name",
          "dataType": "string",
          "validFilters": ["contains", "equal"],
          "enumValues": [],
          "referenceToObj": null,
          "editable": true
        }
      ]
    }
  ]
}
```

- Copy `schemaStatus.fingerprint` to `schemaFingerprint`; set it to `null` only when `object_definitions_list` omitted `schemaStatus`.
- Set `kind` to `standard` only for `account`, `contact`, `deal`, or `employee`; otherwise use `custom`.
- Copy `id` as the canonical field-definition UUID and `fieldId` as the query-facing field key. Do not substitute one for the other.
- Map the MCP response's `type` to `dataType`; use `unknown` only when no type is exposed.
- Set missing `name`, `source`, `referenceToObj`, and `editable` values to `null`; set missing `enumValues` to `[]`.
- Include every field, even when `validFilters` is empty.
- Do not add keys containing sample values, counts, descriptions, transcripts, email content, or record data. The installer rejects unknown keys.

## Install or refresh context

1. Save the completed snapshot to a temporary JSON file using an available file-writing tool. The installer creates `~/.clearskies/` when it does not exist.
2. Resolve the installer path for the current host:
   - Claude Code: `${CLAUDE_PLUGIN_ROOT}/skills/setup-clearskies/scripts/install_context.py`
   - Codex: `scripts/install_context.py` inside the loaded `setup-clearskies` skill directory.
3. When `python3` is available, run:

```bash
python3 <resolved-installer-path> --snapshot-file <temporary-json-file>
```

4. Read the JSON summary printed by the installer. Report:
   - a clear success message: `clearskies is ready` on first setup or `clearskies context refreshed` on later runs;
   - whether this was the first setup;
   - the current plugin version and whether the cached version changed;
   - whether a schema fingerprint was stored;
   - added, removed, or changed objects;
   - added, removed, or changed fields;
   - the four root files plus the per-object profiles under `~/.clearskies/data-profile/`.
   Summarize the result in plain language. Do not expose installer internals unless troubleshooting.
5. Delete the temporary snapshot when the environment permits it.

If `python3` is unavailable, do not install a runtime. Before full discovery, compare the live fingerprint with `schemaFingerprint` in `~/.clearskies/context-metadata.json` and compare the cached `pluginVersion` with the current host manifest. Skip discovery only when both values match and every managed path exists. Otherwise validate the exact snapshot shape above, prepare the four root files and every per-object profile in temporary paths with the host's native file tools, compare the old and new snapshots, and replace the canonical paths only after every discovery and preparation step succeeds. Make `data-profile.md` a small object index and write one compact field-routing file per object under `data-profile/`; keep full field metadata only in `schema-snapshot.json`. Set `context-metadata.json` to schema version `2`, the current host manifest's plugin version, the snapshot's `generatedAt`, and its `schemaFingerprint`. Leave any previous context intact on failure.

Rerun the entire workflow whenever synchronization changes. The installer normalizes the snapshot, compares it with the previous valid snapshot, and updates files atomically.

## Check context freshness without changing it

Call `object_definitions_list`, then run `python3 <resolved-installer-path> --check --schema-fingerprint <schemaStatus.fingerprint>` to compare both the loaded plugin version and live query-relevant CRM schema with `~/.clearskies/context-metadata.json` without filesystem writes. A result of `missing`, `stale`, or `invalid` means setup should be rerun. Recommend the refresh; do not start it automatically during another task without the user's confirmation.

If `object_definitions_list` omits `schemaStatus`, run `--check` without `--schema-fingerprint` to validate the local plugin/cache contract, but report that live schema freshness is unknown. Treat the cached profile only as routing guidance and query the relevant current field schemas before relying on them.

## Optional global loaders

Skill-loaded context is the default and works in both Claude and Codex while keeping unrelated sessions focused. Only after the user explicitly requests and confirms always-on context, rerun the installer with `--install-global-loaders`. That opt-in updates one marked block in each of `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` without creating duplicates, and preserves all other user content. Do not use this option as part of ordinary setup or refresh.
