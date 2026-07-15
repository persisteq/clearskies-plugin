---
name: use-clearskies-revenue-data
description: Query and synthesize revenue context from the clearskies MCP across connected CRM objects, accounts, contacts, deals, employees, meetings, call transcripts, and email. Use whenever a user asks to research an account or person, inspect pipeline or CRM data, prepare for or recap a meeting, find call or email evidence, or answer a revenue question from clearskies outside the workflow builder.
---

# Use clearskies revenue data

Use the available clearskies data without assuming which CRM, objects, fields, or history are connected.

## Load context

1. Read `~/.clearskies/default-guidelines.md` and `~/.clearskies/data-profile.md` when they exist.
2. Otherwise read [references/default-guidelines.md](references/default-guidelines.md).
3. Treat the data profile as a discovery aid, not proof that a record or event still exists. Query the MCP for current answers.

## Choose tools

- Use `object_definitions_list` to discover configured CRM object types.
- Use `object_get_fields_schema` before filtering an unfamiliar object or field. Pass its query-facing `fieldId` and only operators returned in `validFilters`.
- Use `accounts_list`, `contacts_list`, `deals_list`, and `employees_list` for the standard objects.
- Use `account_get_contacts` and `account_get_deals` after identifying an account.
- Use `crm_records_list` only for custom object types returned by `object_definitions_list`.
- Use `records_aggregate` for counts, sums, averages, minimums, maximums, and grouped totals. Never list pages of records merely to count them.
- Treat CRM objects and activity data as separate discovery surfaces. `event` may not appear in `object_definitions_list`; call `object_get_fields_schema` with `objectType: "event"` before using unfamiliar event field filters.
- Use `events_list` for chronological activity or exact filters. Use `events_search` for semantic topic search; entity filters are optional.
- Use `events_get_contents` only after selecting specific event IDs whose transcript, email body, or other content is needed.
- Use `calendar_get_upcoming` only for future calendar windows.
- When exposed, use `support_tickets_list` and `github_activities_list` for their dedicated activity types.
- When exposed, call `identity_get` to verify the signed-in user when identity matters. Prefer `ownedByMe` over manually filtering by the returned person ID.
- When available, `deep_research` starts a longer-running research job. Use it only when the user explicitly requests deep research, then follow its status tool until completion.

## Query safely

1. Resolve entities before requesting their activity. Keep account, contact, employee, internal UUIDs, and external CRM IDs distinct.
2. For Salesforce or Gong identifiers, use `externalIds` rather than text search. Account text search can match names or domains.
3. For “my accounts,” “my contacts,” “my deals,” or “my pipeline,” set `ownedByMe: true`. If it errors, relay the error and do not silently retry without the ownership scope.
4. Prefer exact search when the user supplies an exact name, domain, or email. Retry with a partial or `contains` search when exact search returns nothing.
5. For CRM date-field filters, prefer supported relative values such as `thisQuarter` or `{"relativeDate":"numberOfDaysAgo","value":30}`. Never pass an epoch number as a date.
6. For event periods, apply RFC3339 UTC `startTime` and `endTime`; set `endTime` to now for “recent” or “latest” past activity so future events are excluded.
7. Follow cursors when the answer may span more than one page. Do not claim completeness from a truncated page.
8. Widen a date range only after the requested range returns nothing, and state that the range was widened.
9. Keep reads proportional. Fetch full event contents only for the events used in the answer.
10. For call or transcript requests, inspect the `event` schema before the first `events_list` call when event field filters are needed. Start with explicit time bounds and `internal.type = meeting`. When the recording provider is known, use the top-level `provider` filter to exclude calendar-only meetings. A provider-linked call does not guarantee a transcript: select relevant event IDs, call `events_get_contents`, and verify transcript content before using it. Do not begin with a broad, unfiltered calendar page.

## Synthesize evidence

- Combine CRM state with relevant meeting, email, Slack thread, support-ticket, or GitHub-activity evidence when that improves the answer and those sources are synchronized.
- Identify the source and date of material evidence in the response.
- Distinguish these cases explicitly: no matching record, object or field not synchronized, no events in the requested period, and inaccessible or unauthenticated connector.
- Describe only what clearskies exposes. Do not infer that absent data is absent from the customer's source CRM or communication system.
- Do not use workflow-builder tools unless the user asks to create, change, test, or publish an automation.
- Obtain confirmation before any available tool action that changes CRM or workflow state.
