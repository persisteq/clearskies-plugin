# Clearskies revenue-data guidelines

Clearskies provides tenant-authorized access to synchronized CRM records and revenue interactions such as meetings, call transcripts, and email. Every tenant's CRM, synchronized objects, fields, and history can differ.

## Discovery

- Discover configured object types with `object_definitions_list` instead of assuming Salesforce, HubSpot, or a standard schema.
- Inspect `object_get_fields_schema` before filtering. Use its field IDs and only the operators listed in each field's `validFilters`.
- Treat `account`, `contact`, `deal`, and `employee` as standard objects with dedicated list tools. Query other returned object types with `crm_records_list`.
- Treat the tenant profile in `~/.clearskies/tenant-profile.md` as routing metadata. Query the MCP for current values.

## Search and pagination

- Resolve an account, contact, or employee before asking for its related activity.
- Try exact names, domains, or emails first when the user gives exact identifiers, then retry with partial matching.
- Follow pagination cursors when the requested result may exceed one page.
- Never treat a missing result as proof that the source CRM lacks it. Say whether the record was not found or the object or field is not synchronized.

## Meetings, calls, and email

- Use `events_list` for time-ordered activity and `events_search` for a content question tied to known entities.
- Use explicit RFC3339 UTC time bounds for named periods. For latest past activity, end the range at the current time.
- Select event IDs before calling `events_get_contents`; retrieve only the transcripts or email bodies needed for the answer.
- If the requested period is empty, widen it only when useful and disclose the wider period.

## Answers and safety

- Combine CRM state with dated call or email evidence when it materially improves the answer.
- Name the records or events supporting important conclusions.
- Keep internal employees separate from external contacts.
- Do not expose unrelated customer data or persist record values, transcripts, or email bodies in setup files.
- Do not use workflow tools for ordinary research. Ask for confirmation before changing CRM or workflow state.
