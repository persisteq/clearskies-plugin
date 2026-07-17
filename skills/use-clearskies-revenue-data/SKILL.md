---
name: use-clearskies-revenue-data
description: Query and synthesize revenue context from the clearskies MCP across connected CRM objects, accounts, contacts, deals, employees, meetings, call transcripts, and email. Use whenever a user asks to research an account or person, inspect pipeline or CRM data, prepare for or recap a meeting, find call or email evidence, or answer a revenue question from clearskies outside the workflow builder.
---

# Use clearskies revenue data

Use the available clearskies data without assuming which CRM, objects, fields, or history are connected.

## Load context

1. When `schema_search` is exposed, call it first with the user's business concept and a modest page size. Use its ranked results to select candidate objects and fields. Keep a cursor only with the same query and filters, disclose any warnings, and never treat bounded search results as proof that no other relevant field exists.
2. If `schema_search` is unavailable, use `object_definitions_list` to discover configured objects. This is a live-tool fallback, not a reason to load cached profiles.
3. Call `object_get_fields_schema` for every selected object before filtering, aggregating, or writing. Its response is authoritative for query field IDs, valid operators, enum values, relationships, and write metadata.
4. For audits or verification, use search only to select primary and related objects, then enumerate the complete live schema for each selected object with `object_get_fields_schema`.
5. Do not read `~/.clearskies/data-profile.md`, per-object profiles, or `schema-snapshot.json` during normal task execution. They are legacy setup artifacts, not a substitute for live schema discovery.

## Choose tools

- Use `schema_search` for bounded, cross-object field discovery when exposed. Search is for routing, not exhaustive audit coverage.
- Use `object_definitions_list` when `schema_search` is unavailable or when a complete list of configured CRM object types is needed.
- Use `object_get_fields_schema` before filtering an unfamiliar object or field. Pass its query-facing `fieldId` and only operators returned in `validFilters`.
- Use `accounts_list`, `contacts_list`, `deals_list`, and `employees_list` for the standard objects.
- Use `account_get_contacts` and `account_get_deals` after identifying an account.
- Use `crm_records_list` only for custom object types returned by live schema discovery.
- Use `records_aggregate` for counts, sums, averages, minimums, maximums, and grouped totals. Never list pages of records merely to count them.
- `schema_search` can surface activity objects such as `event` even when `object_definitions_list` omits them. Call `object_get_fields_schema` with the selected activity `objectType` before using unfamiliar filters.
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
9. Fetch full event contents only for the events used in the answer.
10. For call or transcript requests, inspect the `event` schema before the first `events_list` call when event field filters are needed. Start with explicit time bounds and `internal.type = meeting`. When the recording provider is known, use the top-level `provider` filter to exclude calendar-only meetings. A provider-linked call does not guarantee a transcript: select relevant event IDs, call `events_get_contents`, and verify transcript content before using it. Do not begin with a broad, unfiltered calendar page.

## Synthesize evidence

- Combine CRM state with relevant meeting, email, Slack thread, support-ticket, or GitHub-activity evidence when that improves the answer and those sources are synchronized.
- Identify the source and date of material evidence in the response.
- Distinguish these cases explicitly: no matching record, object or field not synchronized, no events in the requested period, and inaccessible or unauthenticated connector.
- Describe only what clearskies exposes. Do not infer that absent data is absent from the customer's source CRM or communication system.
- Do not use workflow-builder tools unless the user asks to create, change, test, or publish an automation.
- Obtain confirmation before any available tool action that changes CRM or workflow state.
