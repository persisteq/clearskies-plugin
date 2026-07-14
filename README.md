# clearskies-plugin

Use Clearskies from **Claude Code** and **ChatGPT (Codex)**. The plugin connects to the
Clearskies MCP, provides guidance for researching synced CRM and revenue-interaction data,
learns each tenant's configured CRM schema, and retains the existing workflow-building skills.

Clearskies can expose tenant-authorized CRM objects and fields, meetings, call transcripts,
and email. Available data depends on the customer's CRM and synchronization settings.

## Connector

The plugin bundles the remote `clearskies` MCP connector:

```text
https://mcp.clearskies.cc/mcp
```

Claude or Codex handles authentication. A user may be prompted to connect Clearskies during
installation or first use; the plugin does not store credentials.

## Skills

- **[use-clearskies-revenue-data](skills/use-clearskies-revenue-data/SKILL.md)** — research
  accounts, contacts, deals, custom CRM records, meetings, transcripts, and email without
  assuming a tenant's CRM schema.
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

Install `clearskies` from the Clearskies marketplace. The `.codex-plugin/plugin.json`
manifest bundles the same connector and skills. Invoke `$setup-clearskies` explicitly or say
`setup clearskies`.

## Set up or refresh tenant context

Run setup after installation and again whenever the customer changes synchronized CRM objects
or fields. Setup reads CRM schema metadata only, then writes the shared source of truth:

```text
~/.clearskies/default-guidelines.md
~/.clearskies/tenant-profile.md
~/.clearskies/schema-snapshot.json
```

It installs one managed loader block in each host's global instructions:

```text
~/.claude/CLAUDE.md
~/.codex/AGENTS.md
```

Existing content outside those marked blocks is preserved. Reruns replace rather than duplicate
the blocks, rediscover the full current schema, and report added, removed, or changed objects and
fields. A failed authentication, incomplete discovery, or invalid snapshot leaves the previous
valid context untouched.

The generated context contains object and field metadata only. It never persists CRM record
values, transcripts, or email bodies.

Workflow skills draft and test changes before publication and never publish or edit live
workflows without explicit approval.
