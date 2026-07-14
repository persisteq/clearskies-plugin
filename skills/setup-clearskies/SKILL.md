---
name: setup-clearskies
description: Set up or refresh clearskies tenant context for Claude and Codex by discovering every synced CRM object and field and generating privacy-safe schema files under ~/.clearskies. Use after installing the clearskies plugin, when a user says "setup clearskies," or whenever CRM objects or synchronized fields have changed.
---

# Setup clearskies

Discover the complete current CRM schema and install shared, rerunnable context for Claude and Codex. Skills load this context only when clearskies work is requested, so setup does not add global context by default.

## Guardrails

- Read metadata only. Do not fetch CRM record values, event contents, transcripts, or email bodies.
- Complete all MCP discovery before invoking the installer. An authentication or discovery failure must leave the last valid files untouched.
- Ask for filesystem approval when the host requires it for writes under the user's home directory.
- Treat `~/.clearskies/default-guidelines.md`, `tenant-profile.md`, and `schema-snapshot.json` as plugin-managed files.
- Do not modify `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md` by default.
- Install global loader blocks only when the user explicitly asks for always-on clearskies context and confirms the global edits. Preserve all content outside the plugin-owned marker blocks.

## Discover the schema

1. Call `object_definitions_list`. If the connector is unavailable or unauthenticated, stop and explain how to connect it.
2. For every returned `objectType`, call `object_get_fields_schema`. Do not omit empty, custom, or unfamiliar objects.
3. Build one JSON snapshot using only this shape:

```json
{
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
   - whether this was the first setup;
   - added, removed, or changed objects;
   - added, removed, or changed fields;
   - the three files under `~/.clearskies`.
5. Delete the temporary snapshot when the environment permits it.

If `python3` is unavailable, do not install a runtime. Validate the exact snapshot shape above, prepare all three complete outputs in temporary files with the host's native file tools, compare the old and new snapshots, and replace the canonical files only after every discovery and preparation step succeeds. Leave any previous context intact on failure.

Rerun the entire workflow whenever synchronization changes. The installer normalizes the snapshot, compares it with the previous valid snapshot, and updates files atomically.

## Optional global loaders

Skill-loaded context is the default and works in both Claude and Codex without global instruction bloat. Only after the user explicitly requests and confirms always-on context, rerun the installer with `--install-global-loaders`. That opt-in idempotently manages one marked block in each of `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`; it preserves all other user content. Do not pass this flag as part of ordinary setup or refresh.
