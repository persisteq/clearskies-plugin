# Microsoft Teams message lookup

As of 2026-07-21, use a channel-based path to find Microsoft Teams messages in the Customer Context Graph.

## Query path

1. Resolve the account, then call `channels_list` and select its channel with source `ms_teams`.
2. Keep the returned Teams channel ID.
3. Call `events_list` with `internal.type isIn ["slack_thread"]`.
4. From those events, select IDs that begin with the Teams channel ID followed by `:`. Event IDs use `{teamsChannelId}:{timestampMs}`, for example `19:...@thread.tacv2:1784660802011`.
5. Fetch contents for only the selected event IDs when message text is needed.

## Why account event filters miss these messages

Teams messages are represented as `slack_thread` events with `content.slack.source: "ms_teams"`, but currently have `entities: []`. Therefore:

- `events_search` with an account entity misses them.
- `events_list` filtered on `internal.accounts` misses them.

Do not interpret an empty account-filtered event result as proof that no Teams messages exist. Fall back to the channel-ID prefix path above.

## Sender caveat

Observed Teams messages had empty `senderName` and `senderEmail` values. Re-verify sender fields before relying on attribution because connector behavior may change.
