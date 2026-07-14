---
name: use-clearskies-revenue-data
description: Query and synthesize revenue context from the Clearskies MCP across tenant-specific CRM objects, accounts, contacts, deals, employees, meetings, call transcripts, and email. Use whenever a user asks to research an account or person, inspect pipeline or CRM data, prepare for or recap a meeting, find call or email evidence, or answer a revenue question from Clearskies outside the workflow builder.
---

# Use Clearskies Revenue Data

Use the tenant's synced Clearskies data without assuming its CRM, objects, fields, or coverage.

## Load context

1. Read `~/.clearskies/default-guidelines.md` and `~/.clearskies/tenant-profile.md` when they exist.
2. Otherwise read [references/default-guidelines.md](references/default-guidelines.md).
3. Treat the tenant profile as a discovery aid, not proof that a record or event still exists. Query the MCP for current answers.

## Choose tools

- Use `object_definitions_list` to discover configured CRM object types.
- Use `object_get_fields_schema` before filtering an unfamiliar object or field. Pass only field IDs and operators returned by that schema.
- Use `accounts_list`, `contacts_list`, `deals_list`, and `employees_list` for the standard objects.
- Use `account_get_contacts` and `account_get_deals` after identifying an account.
- Use `crm_records_list` only for custom object types returned by `object_definitions_list`.
- Use `events_list` for chronological activity and `events_search` for content-oriented questions tied to known account, contact, or employee IDs.
- Use `events_get_contents` only after selecting specific event IDs whose transcript, email body, or other content is needed.
- Use `calendar_get_upcoming` only for future calendar windows.

## Query safely

1. Resolve entities before requesting their activity. Keep account, contact, employee, and external CRM IDs distinct.
2. Prefer exact search when the user supplies an exact name, domain, or email. Retry with a partial or `contains` search when exact search returns nothing.
3. Apply RFC3339 UTC `startTime` and `endTime` bounds whenever the user names a period. Set `endTime` to now for "recent" or "latest" past activity so future events are excluded.
4. Follow cursors when the answer may span more than one page. Do not claim completeness from a truncated page.
5. Widen a date range only after the requested range returns nothing, and state that the range was widened.
6. Keep reads proportional. Fetch full event contents only for the events used in the answer.

## Synthesize evidence

- Combine CRM state with relevant meeting and email evidence when that improves the answer.
- Identify the source and date of material evidence in the response.
- Distinguish these cases explicitly: no matching record, object or field not synchronized, no events in the requested period, and inaccessible or unauthenticated connector.
- Describe only what Clearskies exposes. Do not infer that absent data is absent from the customer's source CRM or communication system.
- Do not use workflow-builder tools unless the user asks to create, change, test, or publish an automation.
- Obtain confirmation before any available tool action that changes CRM or workflow state.
