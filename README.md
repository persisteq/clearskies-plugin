# clearskies-plugin

Use clearskies from **Claude Code** and **ChatGPT (Codex)**. The plugin helps you research
your connected CRM and revenue interactions, learns which CRM objects and fields are available,
and includes guided workflow building.

Available data can include CRM records, meetings, call transcripts, and email, depending on
your connected systems and sync settings.

## Connector

The plugin bundles the remote `clearskies` MCP connector:

```text
https://mcp.clearskies.cc/mcp
```

Claude or Codex handles authentication. A user may be prompted to connect clearskies during
installation or first use; the plugin does not store credentials.

## Skills

- **[use-clearskies-revenue-data](skills/use-clearskies-revenue-data/SKILL.md)** — research
  accounts, contacts, deals, custom CRM records, meetings, transcripts, and email without
  assuming which CRM, objects, or fields are connected.
- **[setup-clearskies](skills/setup-clearskies/SKILL.md)** — discover or refresh every synced
  CRM object and field, then install shared privacy-safe context for Claude and Codex.
- **[clearskies-workflow-builder](skills/clearskies-workflow-builder/SKILL.md)** — author,
  edit, validate, test, and safely publish workflows and agents.
- **[ai-update-salesforce-field](skills/ai-update-salesforce-field/SKILL.md)** — put a
  Salesforce field under AI maintenance using the workflow builder.

## Install

### Claude Code

Add this repository as a marketplace and install the plugin:

```text
/plugin marketplace add persisteq/clearskies-plugin
/plugin install clearskies@clearskies-marketplace
```

Claude namespaces explicit skill commands. For example:

```text
/clearskies:setup-clearskies
```

You can also say `setup clearskies` naturally.

### ChatGPT (Codex)

Install `clearskies` from the clearskies marketplace. The `.codex-plugin/plugin.json`
manifest bundles the same connector and skills. Invoke `$setup-clearskies` explicitly or say
`setup clearskies`.

## Set up or refresh your CRM context

Run setup after installation and again whenever you change synchronized CRM objects
or fields. Setup reads object and field details only, then updates these shared files:

```text
~/.clearskies/default-guidelines.md
~/.clearskies/data-profile.md
~/.clearskies/schema-snapshot.json
```

Clearskies skills read the shared guidelines and data profile only when needed, so this information
does not add context to unrelated Claude or Codex sessions.

Setup does not change global Claude or Codex instructions by default. Users who explicitly want
always-on context can opt in to one managed block in each instruction file:

```text
~/.claude/CLAUDE.md
~/.codex/AGENTS.md
```

The opt-in preserves your existing instructions and does not add duplicate blocks on later runs.
Normal reruns refresh the current objects and fields and report what was added, removed, or changed.
If setup cannot finish, it leaves the previous working context untouched.

The saved context contains object and field details only: field IDs, labels, source names,
types, supported filters, allowed values, references, and editability. It never
persists CRM record values, transcripts, or email bodies.

Workflow skills draft and test changes before publication and never publish or edit live
workflows without explicit approval.
