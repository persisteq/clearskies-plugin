---
name: ai-update-salesforce-field
description: >-
  Put one Salesforce field under AI maintenance with a clearskies workflow: after a
  relevant call, AI finds the right record, checks the transcript is actually useful,
  generates a value, and writes it to the field. Use when a RevOps user wants AI to
  automatically keep a specific SFDC field up to date from meeting content — e.g.
  "have AI keep Opportunity Next Steps updated", "auto-fill our Onboarding Next Step
  field after calls", "update a chosen SFDC field automatically after customer meetings",
  or
  when they pick a field for AI to own. Builds the call-ended → role filter → find
  record → relevance-agent → should-continue gate → generation-agent → updateSalesforce
  pattern, using two reusable field-agnostic agents with all field-specifics in the step
  messages. It proposes or drafts first and never publishes or edits a live workflow
  without explicit approval.
---

# Auto-update a Salesforce field with AI

This skill helps RevOps put **one Salesforce field under AI maintenance**. After a
qualifying call ends, the workflow finds the Salesforce record tied to the meeting's
account, scores whether the transcript is genuinely relevant to the target field,
generates the field's new value if so, and writes it back to Salesforce.

Two AI steps do the work, and both are **reusable and field-agnostic**: a **relevance
agent** and a **generation agent**. Their templates carry no field- or organization-specific
content — everything specific to a field arrives in the step `userMessage`. So the same
two agents serve every field you put under AI maintenance; only the messages change.

It is the field-specific recipe on top of the general clearskies mechanics — for node
shapes, validation, and safe publishing, defer to the **clearskies-workflow-builder**
skill and `workflow_capabilities_get`.

## Load connected-data context

Before trusting cached context, call `object_definitions_list` and retain the exact
`schemaStatus.fingerprint` when present. Run the sibling setup installer's
`--check --schema-fingerprint <live-fingerprint>` mode with Python when available. In
Claude Code, use
`${CLAUDE_PLUGIN_ROOT}/skills/setup-clearskies/scripts/install_context.py`; in Codex,
resolve `../setup-clearskies/scripts/install_context.py` relative to this loaded skill
directory. Read
`~/.clearskies/default-guidelines.md` and `~/.clearskies/data-profile.md` only when the
status is `current` and the live fingerprint was compared. For `missing`, `stale`, or
`invalid`, disclose the status, recommend `setup clearskies`, and read the current bundled
`use-clearskies-revenue-data/references/default-guidelines.md` before continuing with MCP
schema discovery. Do not run setup automatically during another task without confirmation.
Without Python, compare both the live fingerprint with `schemaFingerprint` in
`~/.clearskies/context-metadata.json` and the cached `pluginVersion` with the current host
manifest's `version`. If `schemaStatus` is omitted, live freshness is unknown: use the
profile only as routing guidance and query relevant current schemas. Never use
`lastCheckedAt` as a schema-content version. Treat the data profile as schema-routing
metadata, not current CRM record values.

## Operating rule

Build from the reference pattern, but **never publish or modify a live workflow until
the user explicitly approves that side effect.** Default to a proposed config, or a
draft plus a dry run. A test run (`workflow_test_run_start`) is always safe — it never
writes to Salesforce — so **always dry-run a valid *and* an invalid case before
publishing.** `workflow_validate` confirms shape and that references resolve, but it
does not prove the workflow behaves correctly at runtime.

Read [references/generic-ai-update-pattern.md](references/generic-ai-update-pattern.md)
before generating a config, prompt, or draft — it holds both reusable agent templates
and their `userMessage` templates.

## What it builds

```
trigger-1 (callEnded)
 → filter-1  role gate on meeting.attendees.UserRoleId
 → find-1    the target Salesforce record for {{meeting.accounts.Id}}
 → filter-2  require find-1.records to be non-empty
 → agent-1   reusable RELEVANCE agent (field-specifics in its userMessage)
 → filter-3  continue only if agent-1's output has should_continue: true
 → agent-2   reusable GENERATION agent (field-specifics in its userMessage)
 → updateSalesforce: write {{agent-2.output}} to the field on {{find-1.records.sfRecordId}}
```

Each line shows the node **id** (a `{{...}}` reference handle — it must stay in the
`<type>-<n>` form, e.g. `agent-1`); the ids are numbered in flow order here. Set a
descriptive `data.label` on every node (e.g. *Evaluate relevance*, *Generate field
update*, *Find target record*) — that's the human-readable name shown in the UI.

The order matters: **cheap deterministic filters run first** (role, record-exists, and
any RevOps-chosen gates), **then** the relevance agent and its `should_continue` gate,
and only then the generation agent and the write. Nothing is written unless the
transcript actually clears the relevance bar — this controls cost and prevents
low-quality or empty updates.

`callEnded` requires a filter immediately after the trigger; the role gate (`filter-1`)
satisfies that requirement while also scoping the workflow to the right people.

## Intake — what to confirm with RevOps

Ask only for what's missing. If the user names a target field and gives enough context,
infer the obvious pieces and confirm them in the proposal rather than blocking.

1. **Target field** — `sobjectType` (e.g. `Opportunity`, `Account`,
   `Custom_Object__c`), the field API name, and the human-readable label.
2. **Field semantics** — a definition; what belongs; what must *not* go in it; the
   desired output format (concise note, bullets, plain text, JSON).
3. **Record lookup** — how to find the record from the meeting (usually the target
   object's account field `isIn {{meeting.accounts.Id}}`); any exclusions (status not
   `Complete`, closed opportunities, inactive records, record type); the lookup `limit`
   (default `1`, since the write targets a single record).
4. **Deterministic filters before the AI steps** — the role gate is the baseline;
   optionally require an external attendee, a minimum duration, an account segment, an
   opportunity stage, a title pattern, an owner/role, or "not a placeholder/hold".
5. **Relevance gate** — the score threshold (default `> 3`; raise it to be stricter).
   Use the **reusable relevance agent**; put all field-specific details in its `agent-1`
   `userMessage`, not in the agent template.
6. **Agents & workflow handling** — reuse the existing reusable relevance/generation
   agents or create them (their templates are field-agnostic); the workflow name;
   whether to produce a proposed config, a validate-only check, or a created draft
   (default to a proposed config / validate-only when unsure); and a real test meeting
   id to dry-run against, if available.

## Build procedure

1. Confirm the desired output — a proposed config, a draft, or (with approval) a
   published workflow. Default to a proposed config / draft.
2. Gather the customizations above.
3. Load the reference pattern and resolve the concrete ids it needs (`sobjectType`,
   field API names, the account-lookup field, role ids/names, and the two agent ids) —
   get role ids and the account-lookup field id from an existing workflow's config
   (`workflows_list includeConfig:true`) or `object_get_fields_schema` rather than
   hardcoding or guessing them.
4. Assemble the graph in the order above. Reference the two **reusable** agents by id and
   put everything field-specific in their `userMessage`s (field label, API name,
   definition, what-belongs, exclusions, threshold for `agent-1`; plus output format and
   optional domain context for `agent-2`). Keep the agent templates field-agnostic.
5. Produce the **required fields** from the final config — at minimum:
   `meeting.id`, `meeting.accounts.Id`, `meeting.attendees.UserRoleId`,
   `find-1.records`, `find-1.records.sfRecordId`, `agent-1.output`, `agent-2.output` —
   plus any field introduced by custom filters or lookup conditions.
6. If the workflow MCP tools are available, use `workflow_capabilities_get` and
   `workflow_variables_get` to confirm shapes/variables, `workflow_validate` to check
   the graph, then `workflow_test_run_start` to dry-run. Only after approval use
   `workflows_create`/`workflows_update`, and only after explicit publish approval use
   `workflows_publish`.
7. If tools are unavailable or the user only wants a plan, output the config summary and
   the exact node/edge JSON for review.

## The relevance gate

Relevance is enforced in two nodes: the reusable **relevance agent** (`agent-1`) scores
the transcript 0–10 against the field's definition and returns JSON
(`should_continue`, `score`, `reason`, `relevant_details_found`); then **`filter-3`**
continues only when `should_continue` is true. Keep the threshold at `> 3` unless the
user wants stricter gating, and pass it — with the field definition — in the `agent-1`
`userMessage`. The agent template and both `userMessage` templates are in the reference
file.

## Review checklist

Before presenting the proposed workflow, confirm:

- The update field belongs to the **same object** returned by `find-1`.
- `updateSalesforce.field` uses `find-1.records.<Field_API_Name>` and `recordId` is
  `{{find-1.records.sfRecordId}}`.
- The reusable relevance and generation agent **templates contain no organization- or
  field-specific details** — all of that lives in the `agent-1` / `agent-2`
  `userMessage`s (field label, API name, definition, what-belongs, exclusions,
  threshold, output format).
- Each node has a descriptive `data.label` (e.g. *Evaluate relevance*, *Generate field
  update*, *Find target record*); node **ids** stay in the `<type>-<n>` form because
  `{{...}}` references depend on them.
- `filter-3` gates on `agent-1`'s `should_continue`, and it sits between the two agents.
- Deterministic filters appear **before** the relevance agent.
- `find-1.limit` is `1` (the write is single-record); if RevOps needs to update several
  records per call, wrap the update in a `loop` instead.
- Structured filter `fieldId`s (the role gate and the account lookup) are real for this
  organization — confirm them in a dry run; if `find-1` fails at runtime with `"filter field
  not found"`, switch that condition to an `aiFindPrompt`.
- Both a relevant meeting (proceeds and writes) and an irrelevant one (stops at
  `filter-3`, writes nothing) have been dry-run before any publish.
- Nothing is created or published without explicit user approval.

## Reference & helper files

- `references/generic-ai-update-pattern.md` — the node-by-node template: baseline graph,
  baseline filters, both **reusable agent templates** (relevance + generation), both
  agent `userMessage` templates, the `should_continue` filter, the `updateSalesforce`
  node, the required fields list, and the proposal output shape. Read it before
  generating anything.
