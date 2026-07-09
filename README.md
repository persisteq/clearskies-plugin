# clearskies-plugin

Skills for building and shipping automations on the clearskies
workflow-builder MCP. Each skill lives under `skills/<name>/` with a `SKILL.md` and any
`references/` it needs. The repo is packaged as a plugin (`.claude-plugin/plugin.json`),
so it can be installed directly.

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

Install the whole repo as a plugin, or upload an individual skill's folder via your
Claude workspace / Cowork Skills settings. Every skill proposes or drafts workflows
first and never publishes or edits a live workflow without explicit approval.
