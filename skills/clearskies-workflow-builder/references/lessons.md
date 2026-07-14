# clearskies workflow-builder: lessons & reference

The practical details and traps that `workflow_capabilities_get` omits, with the
patterns that make a shipped workflow behave. Table of contents:

1. The draft / published model
2. Traps, each with evidence and the fix
3. Trigger & node field notes
4. Resolving structured-filter field ids
5. Worked validation: a valid case and invalid cases
6. Worked example: `callEnded` → filter → agent → Slack DM

---

## 1. Draft / published model

- `workflows_create` always makes a **draft** (`published:false`); nothing runs.
- `workflows_update` on a **published** workflow writes a **pending draft**; the live
  version keeps running until you publish. On a draft, the update applies directly.
  After updating something you believe is live, it's still worth a quick
  `workflows_get` / `workflows_list(status:"published")` to confirm it's live before
  telling the user the change shipped.
- `workflows_publish` validates the draft, makes it live, and installs the
  trigger/schedule. **Nothing executes until publish.**
- `workflows_discard_draft` reverts a pending draft; `workflows_unpublish` stops a
  live workflow without deleting it.
- Clean up abandoned drafts with `workflows_delete` / `agents_delete` (soft delete;
  `agents_delete` refuses while the agent is still referenced by a workflow — detach it
  first). `discard_draft` only reverts a *pending draft* on a published workflow; it
  doesn't remove a never-published draft, so use `workflows_delete` for those.
- **Agent-before-workflow:** a `runAgent` node's `agentId` must point at a *published*
  agent or publish fails. Order: `agents_create` → `agents_publish` → reference it →
  publish the workflow.

## 2. Traps (evidence + fix)

### 2.1 `workflow_validate` checks structure and references, not behavior
Validation confirms the graph is well-formed and that its references resolve. It
**rejects**: dangling `{{node.output}}` step refs, `{{...}}` template paths that don't
exist for the trigger, unknown filter `fieldId`s, cyclic graphs, and a `findRecords`
with no selection method; unknown Salesforce objects come back as a non-blocking
**warning**. It also catches bad filter operators, an out-of-range loop limit, an
unpublished agent, a bad `fromUserId`, external email domains, and (for meeting
triggers) a missing lead filter node (see 2.8).

What it **cannot** verify — and why the dry run is mandatory: whether a `findRecords`
returns anything (`count>0`) with real values; `updateSalesforce` single-record
fan-out; a `{{find.records.some_field}}` projection that resolves to empty because the
field name is wrong (validation can't know a record's fields); unsupported date values
(`now-4h`) that parse but never match; and structured-filter `fieldId` resolution on
the workflow path. **Implication: validation guards shape and references; a dry run
owns behavior.**

### 2.2 Structured filter `fieldId` is finicky — prefer AI prompts
`object_get_fields_schema(account)` returns `fieldId` values like `internal.name` /
`salesforce.Custom_Field__c`, and the canonical structured form is
`<source>.<fieldName>` (e.g. `internal.stage`). But a **workflow** `findRecords` filter
can also store an opaque field UUID (a `01…`-style id, not the schema name), and a
structured `fieldId` must resolve on the
workflow path — one that looks correct can still fail at runtime with `"filter field
not found"`. **Fix:** prefer `aiFindPrompt` / `aiFilterPrompt`, which take natural
language (and interpolate `{{...}}`) and sidestep field ids entirely. If you must use a
structured filter, copy the exact `fieldId` from a working workflow's config
(`workflows_list includeConfig:true`) and confirm it in a dry run.

### 2.3 Relationship traversal = chain a find (don't dot the variable tree)
`workflow_variables_get` shows related objects as **drillable references**, not as a
fully-expanded tree, so a relation you want to act on may not appear as a ready-made
dot-path. That doesn't mean it's unreachable: at runtime a record carries its relations
— e.g. an email record contains `accounts`, and `{{find-1.records.accounts}}` resolves
to `[[{"id":…,"name":…}], …]`. The correct pattern for "act on related records":

```
find-1 (emails) → find-2 (accounts, filter isIn {{find-1.records.accounts}}) → act on find-2
```

This is the same idiom used by existing find→find→update workflows (`find → find where
field isIn {{prev.records}} → update {{find.records.sfRecordId}}`).
**Never conclude "unbuildable" from the variable tree — dry-run it.** `aiFindPrompt`
also interpolates `{{prev.records...}}` (via context injection; the stored prompt
still shows the literal `{{...}}` and the resolved values appear only in the step's
`reasoning`).

### 2.4 `updateSalesforce` / `createSalesforce` are single-record
`recordId: {{find-1.records.sfRecordId}}` on a find that returned N>1 updates **only
the first** record and the run still reports `completed` (e.g. 5 accounts found, 1
updated). This is **by design** — fan-out is the loop's job:

```
find-1 → loop {{find-1.records}} → (child, parentNodeId=loop) updateSalesforce recordId={{loop-1.sfRecordId}}
```

The loop child sets `parentNodeId` to the loop id (a sibling of `id`/`data`/`position`,
NOT inside `data`) and has no edge from the loop. The loop fans out to all N
(`iterationPath [0..N-1]`, `itemCount N`).

### 2.5 No sub-day relative dates
Date/timestamp filter values accept: relative keywords (`today`, `yesterday`,
`thisWeek`, `last90Days`, …), the object form `{"relativeDate":"numberOfDaysAgo","value":N}`,
or an absolute RFC3339 timestamp. There is **no hour granularity** and no
`now±Nh`/`now±Nd` token — such strings are accepted at author time and silently do
nothing at runtime. For "last N hours" windows, use an `aiFindPrompt`.

### 2.6 A field projection off a find result resolves to empty string, silently
`{{find-1.records.no_such_field}}` — or any reference that resolves to an empty
collection — resolves to `""`/`[]` at runtime; the step and run report `completed`. For
a Salesforce write this **silently blanks the target field**. (A dangling node id or a
template path the trigger doesn't expose is caught earlier by `workflow_validate`; this
one isn't, because validation can't know a record's fields.) Always read the dry-run
trace and confirm resolved values are real.

### 2.7 Failure / observability notes
- A genuinely failed step (e.g. empty recordId) **does** flip the run to
  `status: failed` — but silent-empty and first-record-only do **not**; they look
  green. Read the trace, don't trust the status.
- `workflow_variables_get` accepts an inline configuration or a saved `workflowId`, and
  returns a compact tree: direct fields as dot-path `systemFields` plus related objects
  as drillable `references` (each with `subFields` and a `drillable` flag) rather than a
  fully-expanded graph. Use it to confirm a `{{...}}` path before referencing it.
- A node may fan out to multiple downstream action nodes (branch), and all execute.

### 2.8 Meeting-triggered workflows require a filter node right after the trigger
This is enforced by `workflow_validate`: a `callStarted`/`callEnded` workflow whose
second node isn't a `filter` fails with `"Meeting workflows must have a filter node
immediately after the trigger; \"<id>\" is not a filter"`. This holds even if you want
the workflow to fire on *every* call — you still need a filter node, just make it a
no-op: `aiFilterPrompt: "always pass"` (the run trace then shows `passed:true` on every
input, with the reasoning naming the "always pass" instruction). Don't confuse this
structural requirement with the meeting-quality guidance in §3, which is about *what*
the filter should check, not *whether* one must exist.

### 2.9 `meeting.*` has no conferencing-link field — don't filter on one
It's tempting to gate call-triggered workflows on "has a real Zoom/Meet/Teams link"
to screen out holds/blocks. **The data doesn't support it.** Three ways to see it:
- `object_get_fields_schema("meeting")` field list: `accounts`,
  `calendar_event_canonical_instance_id`, `calendar_event_source_id`,
  `calendar_event_provider`, `duration_seconds`, `end_at`, `participants`,
  `start_at`, `title`. No url/link field.
- `workflow_variables_get` on a `callEnded` trigger enumerates the full runtime
  `meeting.*` tree: `host`, `attendees`, `accounts`, `participants`,
  `calendar_event_canonical_instance_id`, `calendar_event_source_id`,
  `calendar_event_provider` (the calendar *system*, e.g. google/outlook — not a join
  URL), `duration_seconds`, `end_at`, `id`, `start_at`, `title`. Drilling into
  `meeting.host.*`/`meeting.attendees.*` only adds person-level Salesforce/User
  fields (email, phone, CRM custom fields) — still nothing meeting-level about a
  link.
- `events_get_contents` on a real external call shows the Zoom URL **does exist**,
  but only inside the raw calendar event's free-text `calendarEvent.description`
  (e.g. `"Location: This is a Zoom web conference... https://us02web.zoom.us/j/..."`).
  That `calendarEvent`/`description` field is never surfaced to workflows.

**Consequence:** an `aiFilterPrompt` instructed to require "a real video-conferencing
link" rejects a genuine, already-completed external call that had a full transcript and
AI summary — the model has no link data to check and effectively guesses from the
title, wrongly assuming absence. This is a false negative on production data, not a
hypothetical.

**Fix:** never encode a conferencing-link requirement in a call-trigger filter,
structured or AI. Use fields that are actually in the tree instead —
`duration_seconds` (near-zero for holds that never connected),
`attendees`/`participants` count and `person_type` (external vs. internal), response
status, and title-text heuristics for "Hold"/"Prep"/"Block"/"Busy"/"OOO".

## 3. Trigger & node field notes

- **Triggers:** `callStarted`, `callEnded` (expose `meeting.*`); `scheduled` (no
  `meeting.*`; fields: `scheduleFrequency` = hourly|daily|weekdays|weekly|monthly|custom,
  `scheduleTime`, `scheduleDay`, `scheduleMonthDays`, `scheduleInterval` +
  `scheduleIntervalUnit` (minutes|hours) for custom, `scheduleTimezone` IANA);
  `salesforceRecordCreated` / `salesforceFieldChanged` (expose `record.*`). No
  meeting-anchored "N minutes before a call" trigger exists.
- **Nodes:** `trigger`, `filter` (structured `filter` XOR `aiFilterPrompt`),
  `runAgent` (`agentId` + `userMessage`), `sendSlackMessage`, `findRecords`
  (`objectType`, `limit` 1–100, and exactly one of `filter`/`ids`/`externalIds`/`aiFindPrompt`),
  `updateSalesforce`, `createSalesforce`, `loop` (`loop.input` → array; optional
  `limit`, `runInParallel`), `sendEmail`, `draftEmail`.
- `objectType` values for `findRecords`: `account`, `contact`, `employee`, `deal`,
  `event`, `meeting`, `email`. (`email`/`meeting` are not in `object_definitions_list`
  but are valid here.)
- Step output refs: `{{<id>.output}}` (agent), `{{<id>.records}}` (find),
  `{{loop-1.<field>}}` / `{{loop-1.$value}}` / `{{loop-1.$index}}` (inside loop child).
- `sendEmail`/`draftEmail` `fromUserId` accepts a person's id from `employees_list`
  (or the authenticated user's `userId` from `identity_get`) — either resolves to the sender.

**Call-trigger meeting quality (why call workflows need a real filter).** Calendar
sync excludes only native non-meeting event types — out-of-office, focus time,
working-location, birthday — and cancelled/deleted events (treated as deletes), and
drops events starting more than 1 year out. It does **not** exclude, by title or
availability: personal holds, prep/blocks, placeholders, "busy" entries, declined or
tentative invites, or meetings with **no** conferencing URL — all of these upsert a
meeting row and can fire `callStarted`. So a call-triggered workflow without a
meaningful filter will run on junk meetings and become spammy. `callEnded` is
naturally safer (usually won't fire without a linked, completed call/transcript) but
should still be filtered. See SKILL.md ("Call triggers") for the recommended
quality-gate `aiFilterPrompt` and how to validate it against a real hold/prep event.

## 4. Resolving structured-filter field ids

A structured filter's `fieldId` is organization-specific — often an opaque UUID rather
than the schema name. Don't hardcode ids from elsewhere; get them from the connected organization:

- Read a published workflow that already filters on the field you want
  (`workflows_list includeConfig:true`) and copy its `fieldId` verbatim.
- Or fetch the field via `object_get_fields_schema` (canonical `<source>.<fieldName>`
  form), then confirm it resolves with a dry run (see 2.2).

Common shapes: an account **Name** field for `equal`/`contains`, and a custom object's
account-link field used with `isIn {{find.records}}` to join. Account records carry
`sfRecordId` (the Salesforce id) and an internal `id`; email records carry `accounts`
(array of `{id,name}`) and `participants`
(`{display_name,email_domain,id,person_type,slack_id}`).

## 5. Worked validation (copy this pattern)

Reuse ONE scratch draft. Test runs are **always** dry runs, so writes never hit
Salesforce during testing (trace shows `dryRun:true`) — no flag needed for safety.
`requireHumanReview` is a production-only human-approval gate and irrelevant here.

**Trigger inputs for non-scheduled workflows:** the examples below are scheduled
(no input). For `callStarted`/`callEnded` (needs `meetingId`) and
`salesforceRecordCreated` (needs `recordId`), get **real** inputs from
`workflow_trigger_records_list(workflowId)` (supports `search`); use the object query
tools (`crm_records_list`, `accounts_list`, `deals_list`, `events_list`/`events_search`)
to pick one candidate that satisfies the filter (valid case) and one that violates it
(negative case). Never fabricate a `meetingId`/`recordId` — a made-up id tests nothing.

**Valid case** — update the Acme account's Description (single-record example):
```
scheduled(custom 4h)
 → find-1 findRecords(account, filter fieldId=<account Name field id> equal "Acme", limit 1)
 → sf-1  updateSalesforce(recordId={{find-1.records.sfRecordId}}, sobjectType=Account,
          field=Description, value="hello", requireHumanReview=true)
```
Dry-run expectation: run `completed`; `find-1.count=1`; `sf-1.inputs.recordId` is a
real `001…` id; `sf-1.outputs.dryRun=true, value="hello"`.

**Invalid case A — silent empty:** set `value` to
`"[{{find-1.records.no_such_field}}]"`. Expectation: run `completed` but
`sf-1.outputs.value == "[]"` → proves the reference resolved to nothing (and that
your valid-case values were real, not coincidental).

**Invalid case B — empty find:** change the filter value to a name that matches
nothing. Expectation: `find-1.count=0`, and `sf-1` fails
`"resolved Salesforce record ID is empty"` → run `failed`. Proves the find filters.

**Multi-record probe:** `find(account, limit 5)` → bare
`update {{find-1.records.sfRecordId}}` updates only the first (run `completed`);
adding a `loop` fans out to all 5. Use this to decide whether you need a loop.

## 6. Worked example: `callEnded` → filter → agent → Slack DM

End-to-end pattern for "when a call ends, DM me a summary," including the filter
requirement in 2.8 and a real filter (not just a structural placeholder):

```
trigger-1 callEnded
 → filter-1 filter{type:single, fieldId:"meeting.attendees.person_type",
             operator:"equal", value:"external"}
 → agent-1  runAgent(agentId=<published summarizer agent>, agentInput:"meeting",
             userMessage: Summarize what happened on "{{meeting.title}}" (id: {{meeting.id}}).)
 → slack-1  sendSlackMessage(message:"*Call Summary: {{meeting.title}}*\n\n{{agent-1.output}}",
             recipients:[{type:"user", value:"<slack user id>", label:"<name>"}])
```

Notes to confirm by dry run, not assume:
- `meeting.attendees.person_type` is a literal dot-path field id (not a UUID — 2.2's
  field-id caveat applies to `findRecords` on CRM objects, not to meeting fields), and
  `equal "external"` evaluates true if **any** attendee is external. Confirm via
  `filter-1.outputs.evaluations` in the trace, e.g.
  `{"field":"meeting.attendees.person_type","operator":"equal","result":true}`.
- Valid case: a real external call (has an attendee with `person_type:"external"`) →
  filter `passed:true` → agent produces a grounded summary from actual transcript
  content → Slack step shows `dryRun:true`, a real rendered message, and the correct
  `recipients`/`sent[].target`.
- Negative case: a real internal-only call (e.g. a recurring standup where every
  attendee is `person_type:"internal"`) → filter `passed:false` → run `status:
  "halted"` → agent and Slack steps never run. This is the proof the gate actually
  discriminates, not just that it validates.
- If the agent's summarization instructions don't explicitly forbid it, the model may
  append meta-commentary ("Would you like me to draft a follow-up email?") to the
  end of its output — this then gets forwarded verbatim into the Slack message. Add
  an explicit "Output ONLY the summary text; no questions or offers of further work"
  line to the agent template and re-run the dry run to confirm the appendage is gone.
- Always sanity-check what "every call" means before defaulting to an always-pass
  filter (2.8) — ask what scope is wanted (e.g. external-only, calls you host) rather
  than assuming, then swap the filter and re-dry-run both a satisfying and a
  violating real meeting before re-publishing.
