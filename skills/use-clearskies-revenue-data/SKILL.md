---
name: use-clearskies-revenue-data
description: Query and synthesize revenue context from the clearskies MCP across connected CRM objects, accounts, contacts, deals, employees, meetings, call transcripts, email, Slack, and Microsoft Teams. Use whenever a user asks to research an account or person, inspect pipeline or CRM data, prepare for or recap a meeting, find communication evidence, or answer a revenue question from clearskies outside the workflow builder.
---

# Use clearskies revenue data

Use the available clearskies data without assuming which CRM, objects, fields, or history are connected.

## Discover schema proportionally

- When the relevant object or field is unknown, ambiguous, or cross-object, call `schema_search` with the business concept and a modest page size. Use ranked matches to select candidates, keep cursors with the same query and filters, disclose warnings, and never treat bounded results as exhaustive.
- When the object is known but its field contract is not, call `object_get_fields_schema`. Use its query-facing `fieldId` and only its declared filters, enums, relationships, and write metadata.
- When the object and field IDs have already been verified in the current task, skip schema discovery and query directly.
- Use `object_definitions_list` only for a complete configured-object inventory.
- For an audit, inspect every field on each selected primary and related object. Use `schema_search` to select those objects only when the audit scope is ambiguous.

## Choose tools

- Use `accounts_list`, `contacts_list`, `deals_list`, and `employees_list` for the standard objects.
- Use `account_get_contacts` and `account_get_deals` after identifying an account.
- Use `crm_records_list` only for custom object types returned by live schema discovery.
- Use `records_aggregate` for counts and numeric summaries. Also inspect rows when the user asks for names or examples, when anomalies or data quality matter, or during an audit. Never list pages solely to count them.
- `schema_search` can surface activity objects such as `event` even when `object_definitions_list` omits them. Call `object_get_fields_schema` with the selected activity `objectType` before using unfamiliar filters.
- Use `events_list` for chronological activity or exact filters. Use `events_search` for semantic topic search; entity filters are optional.
- For Microsoft Teams messages, do not start with account-filtered event queries. Read [references/ms-teams-messages.md](references/ms-teams-messages.md) and follow its channel-based lookup path.
- Use `events_get_contents` only after selecting specific event IDs whose transcript, email body, or other content is needed.
- Use `calendar_get_upcoming` only for future calendar windows.
- When exposed, use `support_tickets_list` and `github_activities_list` for their dedicated activity types.
- When exposed, call `identity_get` to verify the signed-in user when identity matters. Prefer `ownedByMe` over manually filtering by the returned person ID.
- When available, `deep_research` starts a longer-running research job. Use it only when the user explicitly requests deep research, then follow its status tool until completion.

## Keep the high-value guardrails

- Resolve an account, contact, or employee before requesting its activity. Before attributing a quote or finding, batch-resolve every cited account, contact, and employee ID with the corresponding list tool. Keep Clearskies UUIDs, people IDs, and external CRM IDs distinct.
- Use `externalIds` for Salesforce or Gong identifiers. Prefer exact names, domains, or emails before partial matching.
- For “my” records or pipeline, set `ownedByMe: true`. If it errors, report the error; never silently remove ownership scope.
- Follow cursors when completeness matters. Do not claim completeness from a truncated page.
- Use supported relative CRM dates or RFC3339/date-only fixed values; never pass epoch numbers. For recent past activity, set explicit UTC bounds with `endTime` equal to now. Disclose any widened range.
- For calls or transcripts, start with bounded meeting filters and use the provider filter when known. A provider-linked event does not prove transcript availability: select event IDs, call `events_get_contents`, and verify transcript content before citing it. Fetch full contents only for events used in the answer.
- Before materially relying on a stored duration, age, score, rollup, or other derived field, check its population and compare it with source fields. If it is unreliable, calculate from the sources when feasible; otherwise report the supported range or limitation instead of false precision.

## Synthesize evidence

- Combine CRM state with relevant meeting, email, Slack thread, support-ticket, or GitHub-activity evidence when that improves the answer and those sources are synchronized.
- Identify the source and date of material evidence in the response.
- Distinguish these cases explicitly: no matching record, object or field not synchronized, no events in the requested period, and inaccessible or unauthenticated connector.
- Describe only what clearskies exposes. Do not infer that absent data is absent from the customer's source CRM or communication system.
- Do not use workflow-builder tools unless the user asks to create, change, test, or publish an automation.
- Obtain confirmation before any available tool action that changes CRM or workflow state.
