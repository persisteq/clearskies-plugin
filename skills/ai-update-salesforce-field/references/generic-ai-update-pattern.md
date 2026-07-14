# Generic AI Update Pattern

The source pattern for putting a Salesforce field under AI maintenance after calls. It
uses two **reusable, field-agnostic agents** — one to score relevance, one to generate
the value — and keeps every field-specific detail in the step `userMessage`. The same
two agents serve every field you put under AI maintenance; only the messages change.

Resolve the concrete ids it needs (object, field, account-lookup field, role, agent)
from this organization — via `workflows_list includeConfig:true`, `object_get_fields_schema`,
or `workflow_variables_get` — or ask; don't hardcode or guess them.

Default trigger: **call ended.**

## Baseline graph

```text
trigger-1 -> filter-1 -> find-1 -> filter-2 -> agent-1 -> filter-3 -> agent-2 -> updateSalesforce
```

Each node's `id` is shown first; the suggested `data.label` (the human-readable name in
the UI) is in *italics*.

- `trigger-1` — call-ended trigger. *Call ended*.
- `filter-1` — role gate on `meeting.attendees.UserRoleId` (also satisfies the
  meeting-trigger requirement that the first node after the trigger is a filter).
  *Attendee role gate*.
- `find-1` — find the target Salesforce record related to `{{meeting.accounts.Id}}`.
  *Find target record*.
- `filter-2` — require `find-1.records` to be non-empty. *Require record found*.
- `agent-1` — reusable **relevance** agent; field-specifics go in its `userMessage`.
  *Evaluate relevance*.
- `filter-3` — continue only if `agent-1`'s output has `should_continue: true`.
  *Relevant enough to continue*.
- `agent-2` — reusable **generation** agent; field-specifics go in its `userMessage`.
  *Generate field update*.
- `updateSalesforce` — write `{{agent-2.output}}` into the target field.
  *Update Salesforce*.

Both AI steps are reusable across every field; the deterministic filters (`filter-1`,
`filter-2`, and any custom gates) run first so the agents only run on qualifying calls.

**Node ids vs. labels.** A node's `id` is a stable reference handle — a variable like
`{{agent-1.output}}` depends on the exact id — and it must be `<node-type-prefix>-<n>`
(`trigger-`, `filter-`, `find-`, and `runAgent` → `agent-`). The ids above are numbered
in flow order for readability, but the id is not the display name: that's the optional
`data.label` on each node. Set the descriptive labels shown in *italics* above so the
workflow reads clearly in the UI, without changing any `{{...}}` reference. (If you edit
incrementally in the UI, new ids are minted as `<prefix>-<max+1>`, so they may not stay
in flow order — the labels are what keep it readable.)

## Baseline filters

**Role gate** (`filter-1`) — use this organization's role ids/names (from an existing
workflow's config or `workflow_variables_get`):

```json
{
  "type": "single",
  "fieldId": "meeting.attendees.UserRoleId",
  "operator": "isIn",
  "value": [
    {"id": "<ORGANIZATION_ROLE_ID>", "name": "<ROLE_NAME>"}
  ],
  "conditions": []
}
```

**Target-record lookup** (`find-1`) — one condition maps the target object's account
field to the meeting's account; add exclusions as needed:

```json
{
  "limit": 1,
  "objectType": "<TARGET_SOBJECT_API_NAME>",
  "filter": {
    "type": "multi",
    "operator": "and",
    "conditions": [
      {
        "type": "single",
        "fieldId": "<TARGET_OBJECT_ACCOUNT_LOOKUP_FIELD_ID_OR_API>",
        "operator": "isIn",
        "value": "{{meeting.accounts.Id}}",
        "conditions": []
      },
      {
        "type": "single",
        "fieldId": "<OPTIONAL_STATUS_FIELD_ID_OR_API>",
        "operator": "notEqual",
        "value": "<EXCLUDED_STATUS>",
        "conditions": []
      }
    ]
  }
}
```

**Existence gate** (`filter-2`) — stop unless a record was found:

```json
{
  "type": "single",
  "fieldId": "find-1.records",
  "operator": "isNotEmpty",
  "value": null,
  "conditions": []
}
```

### Filter field ids & safety

The role gate and the `find-1` account-lookup use structured `fieldId`s. Meeting fields
are literal dot-paths (`meeting.attendees.UserRoleId`), but a CRM-object `fieldId` must
resolve on the workflow path — one that looks right can still fail at runtime with
`"filter field not found"`. Copy the exact `fieldId` from a working workflow's config,
and **confirm `find-1` in a dry run**; if it fails, express the lookup with an
`aiFindPrompt` instead. `find-1.limit` is `1`, so the downstream `updateSalesforce`
targets a single record (wrap it in a `loop` only if a field must be updated on many
records per call).

## Reusable relevance agent (`agent-1`)

Field-agnostic **template / system prompt** — keep it free of any organization- or
field-specific content; that all arrives in the `userMessage`:

```text
You are deciding whether to continue a workflow that may update a Salesforce field based on a meeting transcript.

You will receive a separate user message containing:
- The meeting ID
- The Salesforce field name
- The field description
- What belongs in the field
- What should not be included in the field
- The scoring threshold

Use the meeting ID to retrieve or derive the meeting transcript before making your decision.

Continue only if the meeting transcript contains information that is relevant, specific, and useful enough to reasonably support an update to the provided Salesforce field.

## Evaluation Instructions

Use the provided field name, field description, allowed content, and exclusions as the source of truth for what belongs in the field.

The transcript is relevant only if it contains information that could reasonably be used by a downstream field update agent to produce a valid value for that Salesforce field.

Consider information relevant when it:
- Matches what the field instructions say belongs in the field.
- Avoids what the field instructions say should not be included.
- Is specific enough to support a field update, not just loosely related context.

## Scoring

Assign a numeric score from 0 to 10 based on how useful the transcript is for updating the provided Salesforce field:

- 0: No relevant information for this field.
- 1-3: Weakly related information exists, but it is vague, generic, incomplete, contradicted, or not useful enough to update the field.
- 4-6: Relevant information exists and could support a field update, but may require interpretation or is missing important detail.
- 7-8: Clear, specific, and useful information that would support a confident field update.
- 9-10: Highly specific, complete, and field-ready information requiring little or no interpretation.

## Decision Rule

Continue the workflow only if the score is greater than the scoring threshold from the user message. If no threshold is provided, use greater than 3.

Return only the requested JSON. Do not include follow-up questions, commentary, explanations outside the JSON, markdown, or any other text:

{
  "score": <integer from 0 to 10>,
  "should_continue": <true if score is greater than the threshold, otherwise false>,
  "reason": "<brief explanation of the score>",
  "relevant_details_found": ["<specific transcript detail>", "..."]
}

If no relevant details are found, return an empty array for relevant_details_found.
```

**User message template** for `agent-1` — replace the bracketed values per target field:

```text
# Meeting ID: {{meeting.id}}

# Salesforce field name: [FIELD_LABEL]

# Salesforce field API name: [FIELD_API_NAME]

# Field Description
[FIELD_DEFINITION]

# What belongs in this field
- [BELONGS_1]
- [BELONGS_2]
- [BELONGS_3]

# What should NOT be included
- [EXCLUSION_1]
- [EXCLUSION_2]
- [EXCLUSION_3]

# Scoring threshold
[THRESHOLD]
```

Default threshold: `3`.

## Relevance gate (`filter-3`)

Gate on the relevance agent's decision. An `aiFilterPrompt` reading `agent-1`'s JSON is
the reliable form (it avoids a structured `fieldId` on the agent output):

```text
Continue only if the following relevance check output has should_continue equal to true:
{{agent-1.output}}
```

## Reusable generation agent (`agent-2`)

Field-agnostic **template / system prompt** — again, no organization- or field-specific
content here; it arrives in the `userMessage`:

```text
You are an administrative assistant for a sales team.

You will receive a separate user message containing:
- The meeting ID
- The Salesforce field name
- The Salesforce field API name
- The field description
- What belongs in the field
- What should not be included in the field
- The requested output format
- Optional business or domain context

Review the meeting transcript or communication text for the provided meeting.

Your task is to generate a suggested update for the provided Salesforce field, using only information found in the meeting transcript or communication text.

## Context

Use the provided field name, field description, allowed content, exclusions, and output format as the source of truth for what information is relevant.

Use any provided business or domain context only as background to understand terminology and the operating domain. Do not use this context as evidence for the field update unless the same information is also supported by the meeting transcript or communication text.

## Field Update Instructions

Only include information that:
- Matches what the field instructions say belongs in the field.
- Avoids what the field instructions say should not be included.
- Is directly supported by the meeting transcript or communication text.
- Is specific enough to be useful in the Salesforce field.
- Fits the requested output format.

Do not include information just because it is generally related to the organization, account, opportunity, project, or business relationship. Include only field-specific information supported by the meeting.

## Formatting

Follow the provided output format exactly.

## Rules

- Do not include general discussion, opinions, speculation, or unrelated context.
- Do not add a summary, intro, meta-commentary, explanation, citations, or follow-up questions.
- Output only the generated suggested update for the Salesforce field.
```

**User message template** for `agent-2` — replace the bracketed values per target field:

```text
# Meeting ID: {{meeting.id}}

# Salesforce field name: [FIELD_LABEL]

# Salesforce field API name: [FIELD_API_NAME]

# Field Description
[FIELD_DEFINITION]

# What belongs in this field
- [BELONGS_1]
- [BELONGS_2]
- [BELONGS_3]

# What should NOT be included
- [EXCLUSION_1]
- [EXCLUSION_2]
- [EXCLUSION_3]

# Output format
[OUTPUT_FORMAT]

# Optional business or domain context
[OPTIONAL_BUSINESS_OR_DOMAIN_CONTEXT_OR_NONE]
```

## Update Salesforce node (`updateSalesforce`)

```json
{
  "label": "Update Salesforce",
  "nodeType": "updateSalesforce",
  "updateSalesforce": {
    "sobjectType": "<TARGET_SOBJECT_API_NAME>",
    "field": "find-1.records.<TARGET_FIELD_API_NAME>",
    "value": "{{agent-2.output}}",
    "recordId": "{{find-1.records.sfRecordId}}"
  }
}
```

`requireHumanReview: true` (optional) holds the live write as a suggestion for a rep to
approve instead of auto-applying it — a production choice, unrelated to testing (test
runs never write regardless).

## Required fields

Always include, plus any field introduced by custom filters or lookup conditions:

```json
[
  "agent-2.output",
  "agent-1.output",
  "find-1.records",
  "find-1.records.sfRecordId",
  "meeting.accounts.Id",
  "meeting.attendees.UserRoleId",
  "meeting.id"
]
```

## Proposal output shape

When the user asks for the proposed workflow, return:

1. Assumptions and unanswered questions.
2. Node order.
3. Filter list (baseline + custom).
4. Reusable **relevance** agent template + its `agent-1` `userMessage`.
5. Reusable **generation** agent template + its `agent-2` `userMessage`.
6. `updateSalesforce` config.
7. Required fields.
8. Next step: validate-only, create draft, update draft, or publish (with the reminder
   that a valid *and* invalid dry run should precede any publish).
