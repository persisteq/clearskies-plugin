# clearskies revenue-data guidelines

clearskies provides access to synchronized CRM records and revenue interactions such as meetings, call transcripts, email, Slack threads, support tickets, and GitHub activity. Available objects, fields, sources, and history depend on the connected systems and sync settings.

## Discovery

- Discover configured object types with `object_definitions_list` instead of assuming Salesforce, HubSpot, or a standard schema.
- Compare `schemaStatus.fingerprint` from `object_definitions_list` with the full cached `schemaFingerprint` before trusting the saved data profile. Treat a mismatch as stale schema. Do not use `lastCheckedAt` for this comparison; it is a refresh timestamp, not a content version.
- Inspect `object_get_fields_schema` before filtering. Use its query-facing `fieldId` and only the operators listed in each field's `validFilters`.
- Treat `account`, `contact`, `deal`, and `employee` as standard objects with dedicated list tools. Query other returned object types with `crm_records_list`.
- Treat `~/.clearskies/data-profile.md` as a small routing index. Open only the linked object profile files relevant to the question; never read all object profiles or the full `schema-snapshot.json` by default. If a selected profile cannot be read, disclose the fallback and call `object_get_fields_schema` for that object instead of silently skipping discovery or broadly grepping cached files. Query the MCP for current values.
- Use `identity_get` when exposed and the signed-in user matters. Prefer server-side `ownedByMe` scoping over manually resolving an owner ID.

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

- Activity data is separate from CRM object discovery. `event` may not appear in `object_definitions_list`; this does not mean activity data is unavailable. Before applying event field filters, call `object_get_fields_schema` with `objectType: "event"`.
- Use `events_list` for time-ordered browsing, exact entity filters, and event types. Synced types can include `meeting`, `email`, `slack_thread`, `support_ticket`, and `github_activity`.
- Use `events_search` for semantic topic questions. Entity filters can narrow a search but are not required.
- Use explicit RFC3339 UTC time bounds for named periods. For latest past activity, end the range at the current time.
- For call or transcript requests, inspect the `event` schema before the first `events_list` call when event field filters are needed. Start with explicit time bounds and an `internal.type = meeting` filter instead of fetching a broad, unfiltered calendar page.
- When the recording provider is known, use the top-level `provider` filter to exclude calendar-only meetings. This returns meetings linked to a call from that provider; it does not guarantee that transcript content is available.
- Select event IDs before calling `events_get_contents`; retrieve only the transcripts or email bodies needed for the answer.
- Verify that transcript content exists before describing an event as a call with a transcript.
- If the requested period is empty, widen it only when useful and disclose the wider period.
- When exposed, use `support_tickets_list` and `github_activities_list` for focused ticket or engineering-activity queries.

## Match investigation effort to the question type

- **Lookup** (one fact or record): use minimum calls; stop once confirmed.
- **Metric or report** (counts, sums, or breakdowns): aggregate first; verify the headline total one independent way, such as confirming that grouped counts sum to the top-line count, then stop. Do not independently re-derive every sub-series or period unless the cross-check disagrees.
- **Synthesis across content** (themes, feedback, or objections across calls or email): run multiple query angles with different phrasings; stop at saturation, when a new angle surfaces nothing new, not at a call budget.
- **Audit or verification**: take an adversarial stance; re-derive numbers rather than trusting prior summaries or the data profile; follow anomalies where they lead instead of completing a fixed checklist.

**Audit the full relevant object profiles.** For audit or verification questions, use the `data-profile.md` index to select the primary objects and any related objects whose fields could affect eligibility, attribution, status, or aggregation, then inspect every field label and query field ID in those object files once. Do not load unrelated object profiles or limit discovery within a selected profile to keyword matches based on the initial hypotheses. Consider indirect eligibility, suppression, lifecycle, status, and quality signals before selecting checks. Call `object_get_fields_schema` only when the cached context is missing or stale, a relevant object or field is absent, full filter/enum metadata is needed, or live tool behavior conflicts with the profile.

**Validate derived fields before aggregating them.** Before treating a stored duration, age, score, rollup, or other derived field as authoritative, check its population coverage and compare it with its source fields on raw records that include null, typical, and extreme values. If it is sparse, contradictory, or contains impossible values, compute the metric from source fields over the complete in-scope row set when feasible. Otherwise disclose the bound and do not present the result as exact. A correct row-derived answer is better than a fast aggregate of a broken field.

**Resolve cited entity IDs before attribution.** Event search results identify accounts, contacts, and employees by entity ID. Before finalizing an answer that attributes a quote or finding, batch the IDs you will cite by entity type and resolve them with the corresponding `accounts_list`, `contacts_list`, or `employees_list` `ids` filter. Request only the identity fields needed and set `itemsPerPage` to cover the batch when supported. Use one call per entity type when the cited IDs fit one page; follow cursors only when they do not. Entity resolution is part of answer completeness, not discretionary polish—proportionality does not apply to it. Do not substitute transcript handles for named people or companies when resolvable entity IDs are available.

**Disclose rather than truncate.** Proportionality limits redundancy, never silently limits coverage. If you cap effort, state exactly what was not searched, such as "one semantic pass; narrower queries could surface more." Never present a bounded search as exhaustive.

## Answers and safety

- Combine CRM state with dated call or email evidence when it materially improves the answer.
- Name the records or events supporting important conclusions.
- Keep internal employees separate from external contacts.
- Do not expose unrelated customer data or persist record values, transcripts, or email bodies in setup files.
- Do not use workflow tools for ordinary research. Ask for confirmation before changing CRM or workflow state.
- When available, `deep_research` starts a longer-running research job. Use it only when the user explicitly asks for deep research, then check its status as instructed until it finishes.
