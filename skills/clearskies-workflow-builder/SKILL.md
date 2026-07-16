---
name: clearskies-workflow-builder
description: >-
  Author, edit, validate, and safely publish workflows and agents on the clearskies workflow-builder MCP (tools
  workflow_capabilities_get, workflows_create/update/publish, workflow_validate,
  workflow_variables_get, workflow_test_run_start, workflow_runs_get/list, agents_*,
  object_*). Use whenever the user wants to build, change, debug, or publish a
  clearskies workflow or agent — e.g. "make a workflow that…", "update the
  workflow that…", "why did my workflow fail", "publish this workflow" — or describes a
  scheduled/call/Salesforce-triggered automation that finds CRM records, runs an agent,
  posts Slack, sends email, or writes Salesforce, even without saying "workflow" (e.g.
  "every morning DM me my open deals"). Key rule: workflow_validate checks structure and
  references but not runtime behavior, so ALWAYS dry-run with workflow_test_run_start
  before publishing.
---

# clearskies workflow builder

Building a clearskies workflow looks easy and is full of quiet traps. The tools
happily accept configurations that validate clean and then silently misbehave at
runtime — writing to the wrong record, resolving a variable to empty string, or
finding nothing. This skill encodes the order of operations and the specific traps
so a workflow you ship actually does what the user asked.

## Load connected-data context

Before trusting cached context, run the sibling
`setup-clearskies/scripts/install_context.py --check` with Python when available. Resolve
it inside the loaded plugin directory; in Claude Code it is
`${CLAUDE_PLUGIN_ROOT}/skills/setup-clearskies/scripts/install_context.py`. Read
`~/.clearskies/default-guidelines.md` and `~/.clearskies/data-profile.md` only when the
status is `current`. For `missing`, `stale`, or `invalid`, disclose the status, recommend
`setup clearskies`, and read the current bundled
`use-clearskies-revenue-data/references/default-guidelines.md` before continuing with MCP
schema discovery. Do not run setup automatically during another task without confirmation.
Without Python, compare `pluginVersion` in `~/.clearskies/context-metadata.json` with the
current host manifest's `version`. Treat the data profile as schema-routing metadata, not
current CRM record values.

## The golden rule

**`workflow_validate` confirms the graph is well-formed and that its references
resolve** — it rejects dangling `{{...}}` references, template paths a trigger doesn't
expose, unknown filter `fieldId`s, cycles, and a `findRecords` with no selection method
(unknown Salesforce objects come back as a warning). **What it cannot do is prove the
workflow behaves correctly at runtime:** whether a find actually returns records, that
an `updateSalesforce` targets more than the first record, that a
`{{find.records.some_field}}` projection resolves, or that a structured filter's
`fieldId` resolves on the workflow path. A `{"valid": true}` means "well-formed and
references exist," not "this works." The only trustworthy behavioral check is a **dry
run** (`workflow_test_run_start` → `workflow_runs_get`), where you read the actual
per-step inputs and outputs. Never publish on validation alone.

## Order of operations

Follow these in order. Don't skip to publishing.

1. **Read the available workflow capabilities.** Call `workflow_capabilities_get` first — node
   types, trigger types, and other options can change over time. It is the source of truth
   for shape; `references/lessons.md` is the
   source of truth for the traps it omits.
2. **Learn from a working example.** Call `workflows_list` with `includeConfig: true`
   and read a published workflow similar to the target. This is how you discover real
   filter field ids and proven node shapes — see the "field IDs" trap below.
3. **Design the graph**, applying the traps in `references/lessons.md`. Add a
   `runAgent` node only if the task needs real AI reasoning; skip it for pure data
   forwarding.
4. **Create or update as a draft** (`workflows_create` / `workflows_update`). Both
   write a draft; nothing runs until you publish. On a published workflow,
   `workflows_update` writes a pending draft and leaves the live version untouched
   until you publish. For incremental edits to an existing draft, `workflow_node_patch`
   applies an ordered batch of add/update/replace/delete node ops (wiring the edges for
   you) without resending the whole config; it's mutate-only, so still validate and
   publish afterward. Use `workflows_update` with the full configuration when you need
   parallel branches.
5. **Validate** (`workflow_validate`) and fix the per-node errors. Necessary but not
   sufficient.
6. **VALIDATE BY DRY RUN — the mandatory step.** See the next section. Do not skip
   this even if validation passed and the graph "looks obviously correct."
7. **Publish** (`workflows_publish`) only after the dry run confirms behavior. If the
   workflow references an agent, publish the agent first (`agents_publish`) — a
   workflow can't publish while pointing at an unpublished agent.

## The mandatory validation step (valid + invalid dry runs)

Validation that only runs the happy path tells you little. Prove the workflow both
*does the right thing* on good input and *visibly fails* on bad input — that
confirms your assertions actually discriminate, and it surfaces the silent-empty
and wrong-record traps that `workflow_validate` cannot.

**Safety:** `workflow_test_run_start` is **always** a dry run — it never writes to
Salesforce (write steps report `dryRun: true` and show the exact recordId/field/value
they *would* have written), and no Slack message or email is actually sent. Testing is
therefore safe by construction; you do not need any special setting to protect a test run.

`requireHumanReview` is a **production-only** control, unrelated to testing: on a
*live/published* workflow it holds the Salesforce write for a human to approve instead
of auto-applying it. Decide it by production intent — set it when you want a human in
the loop on live writes; leave it off when you want the published workflow to
auto-write. Neither of these facts — that test runs never write, and that this setting
is production-only — is stated in the tool docs, so make it explicit to whoever
inherits the workflow.

**Procedure:**

1. **Pick a real trigger input (non-scheduled triggers).** Scheduled triggers need no
   input. Call triggers (`callStarted`/`callEnded`) need a `meetingId`; record triggers
   (`salesforceRecordCreated`) need a `recordId`. **Never fabricate these ids** — query
   the MCP for real data: `workflow_trigger_records_list(workflowId)` returns valid
   candidate inputs for that workflow's trigger (meetings or records), with `search`.
   To choose deliberately, confirm which candidates satisfy vs. violate your
   workflow's filter using the object query tools (`crm_records_list`, `accounts_list`,
   `deals_list`, `events_list`/`events_search`, `object_get_fields_schema`). Testing on
   real records is what makes the dry run meaningful — a made-up id tests nothing.
2. **Run the valid case.** `workflow_test_run_start` with the chosen real input (a
   `recordId` or `meetingId` that *does* meet the workflow's condition; none for
   scheduled). Poll `workflow_runs_get <testRunId>`.
   Run traces containing emails/accounts are large (50–80 KB) and will overflow —
   **extract with `jq`, never read the whole blob** (`scripts/inspect_run.sh` does
   this for you).
   - Assert: run `status: completed`; each step `completed`; the resolved
     `inputs`/`outputs` contain **real values** — real `sfRecordId`s, non-empty
     fields, expected `count > 0`. An empty `count`, an empty `recordId`, or a
     value like `"FIELD=[]"` means a reference silently resolved to nothing.
3. **Run at least one invalid/negative case** — confirm the workflow does the right
   thing when it *shouldn't* fire or when a reference is wrong. Choose the probe by
   trigger type:
   - **Non-scheduled triggers → feed a real record/meeting that legitimately lacks the
     condition.** Don't fabricate an id and don't mangle the config — pull a genuine
     counter-example via `workflow_trigger_records_list` (+ the object query tools to
     find one that violates the filter), pass its real `recordId`/`meetingId`, and
     confirm the workflow stops at the filter / produces no action. This proves the
     gating works on real data the way production will see it.
   - **Reference integrity (any trigger)** — a **field projection off a find result**
     (`{{find-1.records.no_such_field}}`) resolves to an empty string silently:
     validation can't know a record's fields, so the run still reports success. Confirm
     it resolves to a real value, which also proves your happy-path values weren't
     accidental.
   - **Empty find** → confirm `count: 0` and that a downstream single-record
     `updateSalesforce` then errors `"resolved Salesforce record ID is empty"` (proves
     the find is actually filtering).
   - **Multi-record find feeding a bare update** (no loop) → confirm only the **first**
     record is targeted (the single-record trap).
4. **Compare against expectation and report.** State plainly what each run proved.
   Only after the valid case behaves and the invalid case fails-as-expected should
   you publish.

If a dry run contradicts your mental model, trust the trace and fix the graph —
that is the entire point of this step.

## Call triggers (`callStarted` / `callEnded`): screen out non-meetings

Calendar sync is a coarse filter. It excludes only *native* non-meeting event types
(out-of-office, focus time, working-location, birthday) and cancelled events, and it
drops events starting more than a year out. **Everything else becomes a meeting the
trigger can fire on** — including ordinary personal **holds, prep/blocks,
placeholders, "busy" entries, and declined or tentative invites.** None of those are
screened by title or availability at the trigger layer.

The consequence: a `callStarted` workflow with no real filter will fire on someone's
"Hold — do not book" or "Prep" block and spam Slack/email/Salesforce. (`callEnded` is
naturally safer — it generally won't fire for a pure hold because there's no linked,
completed call/transcript — but filter it too; don't rely on that.)

**Do not filter on "has a video-conferencing link."** It's tempting to add "has a real
Zoom/Meet/Teams link" as a quality signal, and it seems like the obvious way to reject
holds/blocks — but the `meeting.*` data a workflow can see has **no such field**.
`object_get_fields_schema(meeting)` and `workflow_variables_get` both cap out at:
`accounts`, `attendees`, `calendar_event_canonical_instance_id`,
`calendar_event_source_id`, `calendar_event_provider` (which calendar system, e.g.
Google/Outlook — not a join link), `duration_seconds`, `end_at`, `host`, `id`,
`participants`, `start_at`, `title`. The actual Zoom/Meet URL lives only in the raw
calendar event's free-text `description` (visible via `events_get_contents`), a field
workflows never receive. An `aiFilterPrompt` asked to check for a link is therefore
guessing from the title/attendees with no real signal, and it **will false-negative on
genuine, already-recorded customer calls**. If you need to reject non-calls, use
signals that are actually exposed: `duration_seconds` (a 0-duration or never-started
hold has none/very little), attendee count and `person_type`, response status, and
title text — not a conferencing-link check.

**So every call-triggered workflow needs a filter node right after the trigger that is
a real quality gate, not a rubber stamp.** (Call-triggered workflows are required to
have a filter immediately after the trigger anyway — make that requirement earn its
keep.) Decide what "a real meeting worth acting on" means for the use case, then
encode it. A good general-purpose `aiFilterPrompt` default:

```
Only proceed if this is a genuine meeting worth acting on:
- it has at least one attendee outside our own company (an external/customer domain),
- the current user has NOT declined it,
- it has a nonzero duration (duration_seconds > 0) consistent with a call that
  actually happened, and
- it is NOT a personal hold, focus/time block, prep or reminder, or placeholder
  (e.g. titles like "Hold", "Prep", "Block", "Busy", "OOO", "Placeholder", "Focus",
  "Reminder", or an empty/1-attendee event).
Otherwise stop.
```

Tighten or loosen per use case — an internal-standup digest wants the opposite of the
"external attendee" clause. Prefer `aiFilterPrompt` here because hold/prep/placeholder
detection is fuzzy and title-dependent; use a structured `filter` when you have a
crisp signal (e.g. attendee count, a known internal domain, response status) — but
never a conferencing-link check, structured or AI, since the data isn't there.

**Validate it with a real junk meeting.** This is the ideal negative case for the
mandatory validation step: use `workflow_trigger_records_list` to find a real "Hold"
/ "Prep" / calendar-block event, dry-run it, and confirm the workflow stops
at the filter. Then dry-run a real customer meeting and confirm it proceeds.

## The traps (read before building)

Full detail, with evidence, is in `references/lessons.md`. The ones that bite most:

- **Prefer `aiFilterPrompt` / `aiFindPrompt` over structured filters.** A structured
  filter's `fieldId` is finicky — it must resolve on the workflow path, and one that
  looks right can still fail at runtime with `"filter field not found"`. The AI-prompt
  forms take natural language (and interpolate `{{...}}`), sidestep field ids, and are
  the reliable default. If you must use a structured filter, copy the exact `fieldId`
  from a working workflow's config (`workflows_list includeConfig:true`) and confirm it
  in a dry run.
- **Traverse relationships by chaining finds, not by dotting the variable tree.**
  To act on records related to a prior step, add a second `findRecords` filtered
  `isIn {{find-1.records}}` (or `{{find-1.records.<field>}}` / `<relation>`), then act
  on `{{find-2.records.sfRecordId}}`. Relations resolve at runtime **even when
  `workflow_variables_get` omits them** — don't conclude "unreachable" from the
  variable tree; a dry run is the arbiter.
- **`updateSalesforce` is single-record.** `{{find.records.sfRecordId}}` targets only
  the **first** record and still reports `completed`. To update N records, wrap the
  update in a `loop` over `{{find.records}}` and use `{{loop-1.sfRecordId}}`.
- **No sub-day relative dates.** Date filters support day-granular relatives
  (`yesterday`, `{"relativeDate":"numberOfDaysAgo","value":N}`) or RFC3339 — there is
  no "last 4 hours". For short windows use an `aiFindPrompt` ("emails in the last 4
  hours"). `now-4h`-style strings are accepted silently and never work.
- **A field projection off a find result can resolve to empty silently.**
  `{{find-1.records.no_such_field}}` — or any reference that resolves to an empty
  collection — becomes `""`/`[]` at runtime with no error; for a Salesforce write that
  blanks the target field. Always confirm resolved values in the dry-run trace.
- **Use `workflow_variables_get` to confirm a `{{...}}` path exists.** It takes an
  inline configuration you're drafting *or* a saved `workflowId`, and returns a compact
  tree — direct fields as dot-path `systemFields`, related objects as drillable
  `references` (`subFields` / `drillable`) rather than a fully-expanded graph. Reference
  only paths it confirms, but remember relations resolve at runtime even before you
  drill them (see the relationship-traversal trap in `references/lessons.md`).
- **A `runAgent` summarizer may append meta-commentary** ("want me to draft a
  follow-up?") to its output, which then flows verbatim into a Slack message or
  email. If the agent's job is to produce a message body, tell its template
  explicitly to output only that text with no questions or offers of further work,
  and confirm the fix in a dry run.

## Reference & helper files

- `references/lessons.md` — the complete, evidence-backed trap list, the draft/publish
  model, trigger/node field details, known organization field ids, and worked
  valid/invalid dry-run examples. Read it before building anything non-trivial.
- `scripts/inspect_run.sh` — `bash scripts/inspect_run.sh <run-json-file>` prints the
  per-step status/errors and resolved inputs/outputs from an overflowed
  `workflow_runs_get` result without dumping the whole blob into context.
