# clearskies revenue-data guidelines

clearskies provides authorized access to synchronized CRM records and revenue interactions such as meetings, call transcripts, email, Slack threads, support tickets, and GitHub activity. Every organization's CRM, synchronized objects, fields, sources, and history can differ.

## Discovery

- Discover configured object types with `object_definitions_list` instead of assuming Salesforce, HubSpot, or a standard schema.
- Inspect `object_get_fields_schema` before filtering. Use its query-facing `fieldId` and only the operators listed in each field's `validFilters`.
- Treat `account`, `contact`, `deal`, and `employee` as standard objects with dedicated list tools. Query other returned object types with `crm_records_list`.
- Treat the data profile in `~/.clearskies/data-profile.md` as routing metadata. Query the MCP for current values.
- Use `identity_get` when exposed and the authenticated user or organization matters. Prefer server-side `ownedByMe` scoping over manually resolving an owner ID.

## Search and pagination

- Resolve an account, contact, or employee before asking for its related activity.
- Use `externalIds` for Salesforce or Gong identifiers. Keep external IDs, clearskies UUIDs, and people IDs distinct.
- Try exact names, domains, or emails first when the user gives exact identifiers, then retry with partial matching. Account search can match company names and domains.
- For “my accounts,” “my contacts,” “my deals,” or “my pipeline,” pass `ownedByMe: true`. If that errors, relay the message and never silently remove the ownership scope.
- Follow pagination cursors when the requested result may exceed one page.
- Never treat a missing result as proof that the source CRM lacks it. Say whether the record was not found or the object or field is not synchronized.

## Aggregation and CRM dates

- Use `records_aggregate` for counts and numeric summaries; do not list and count records page by page.
- Before aggregating or filtering, discover the field schema and use only supported fields, types, and operators.
- For CRM date fields, prefer relative filters such as `thisQuarter` or `{"relativeDate":"numberOfDaysAgo","value":30}` when the tool supports them.
- Use RFC3339 or date-only strings for fixed calendar dates. Never use Unix or epoch numbers as dates.

## Meetings, calls, and email

- Use `events_list` for time-ordered browsing, exact entity filters, and event types. Synced types can include `meeting`, `email`, `slack_thread`, `support_ticket`, and `github_activity`.
- Use `events_search` for semantic topic questions. Entity filters can narrow a search but are not required.
- Use explicit RFC3339 UTC time bounds for named periods. For latest past activity, end the range at the current time.
- Select event IDs before calling `events_get_contents`; retrieve only the transcripts or email bodies needed for the answer.
- If the requested period is empty, widen it only when useful and disclose the wider period.
- When exposed, use `support_tickets_list` and `github_activities_list` for focused ticket or engineering-activity queries.

## Answers and safety

- Combine CRM state with dated call or email evidence when it materially improves the answer.
- Name the records or events supporting important conclusions.
- Keep internal employees separate from external contacts.
- Do not expose unrelated customer data or persist record values, transcripts, or email bodies in setup files.
- Do not use workflow tools for ordinary research. Ask for confirmation before changing CRM or workflow state.
- `deep_research` starts a feature-gated research job and is not an ordinary read. Use it only when the user explicitly asks for deep research, then poll its status tool as instructed.
