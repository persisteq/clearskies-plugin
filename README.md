# clearskies-plugin

Skills for building and shipping automations on the clearskies workflow-builder MCP —
usable from both **Claude Code** and **ChatGPT (Codex)**. Each skill lives under
`skills/<name>/` with a `SKILL.md` and any `references/` it needs. The repo ships a plugin
manifest for each host — `.claude-plugin/plugin.json` and `.codex-plugin/plugin.json` — and
is also its own Claude Code marketplace (`.claude-plugin/marketplace.json`).

## Skills

- **[clearskies-workflow-builder](skills/clearskies-workflow-builder/SKILL.md)** — author,
  edit, validate, and safely publish workflows and agents on the workflow-builder MCP.
  Encodes the order of operations and the runtime traps that validation can't catch, and
  enforces the golden rule: always dry-run before publishing.
- **[ai-update-salesforce-field](skills/ai-update-salesforce-field/SKILL.md)** — put one
  Salesforce field under AI maintenance: after a relevant call, the workflow finds the
  right record, checks the transcript is useful for that field, generates a value, and
  writes it. The RevOps recipe for "have AI keep this field up to date." Builds on the
  general skill above.

## Installing

### Claude Code

Add this repo as a marketplace, then install the plugin:

```
/plugin marketplace add persisteq/clearskies-plugin
/plugin install clearskies@clearskies-marketplace
```

The plugin bundles both skills. Skills are namespaced, e.g. `/clearskies:clearskies-workflow-builder`.

### ChatGPT (Codex)

The repo also ships a `.codex-plugin/plugin.json` manifest (plus brand assets under
`assets/`) that describes the plugin for ChatGPT (Codex), so the same two skills are
available there.

Every skill proposes or drafts workflows first and never publishes or edits a live
workflow without explicit approval.
