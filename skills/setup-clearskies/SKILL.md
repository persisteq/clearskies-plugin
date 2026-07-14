---
name: setup-clearskies
description: Set up or refresh Clearskies tenant context for Claude and Codex by discovering every synced CRM object and field, generating privacy-safe schema files under ~/.clearskies, and installing managed global-instruction loaders. Use after installing the Clearskies plugin, when a user says "setup clearskies," or whenever CRM objects or synchronized fields have changed.
---

# Setup Clearskies

Discover the complete current CRM schema and install shared, rerunnable context for Claude and Codex.

## Guardrails

- Read metadata only. Do not fetch CRM record values, event contents, transcripts, or email bodies.
- Complete all MCP discovery before invoking the installer. An authentication or discovery failure must leave the last valid files untouched.
- Ask for filesystem approval when the host requires it for writes under the user's home directory.
- Treat `~/.clearskies/default-guidelines.md`, `tenant-profile.md`, and `schema-snapshot.json` as plugin-managed files.
- Preserve all non-managed content in `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md`.

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
          "id": "field-id",
          "label": "Account Name",
          "name": "Name",
          "dataType": "string",
          "validFilters": ["contains", "equal"]
        }
      ]
    }
  ]
}
```

- Set `kind` to `standard` only for `account`, `contact`, `deal`, or `employee`; otherwise use `custom`.
- Use `unknown` when field metadata does not expose a data type.
- Set `name` to `null` when no API or source name is exposed.
- Include every field, even when `validFilters` is empty.
- Do not add keys containing sample values, counts, descriptions, transcripts, email content, or record data. The installer rejects unknown keys.

## Install or refresh context

1. Resolve this skill's directory and save the completed snapshot to a temporary JSON file using an available file-writing tool.
2. Run:

```bash
python3 <setup-clearskies-skill-dir>/scripts/install_context.py --snapshot-file <temporary-json-file>
```

3. Read the JSON summary printed by the installer. Report:
   - whether this was the first setup;
   - added, removed, or changed objects;
   - added, removed, or changed fields;
   - the three files under `~/.clearskies` and both managed host loaders.
4. Delete the temporary snapshot when the environment permits it.

Rerun the entire workflow whenever synchronization changes. The installer normalizes the snapshot, compares it with the previous valid snapshot, updates files atomically, and replaces existing managed loader blocks instead of duplicating them.
