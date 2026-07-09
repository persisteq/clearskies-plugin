#!/usr/bin/env bash
# Summarize a workflow_test_run_start / workflow_runs_get result without dumping
# the whole (often 50–80 KB) blob into context.
#
# Usage:
#   bash inspect_run.sh <run-json-file>
#
# When workflow_runs_get overflows, the harness saves the JSON to a file and prints
# its path — pass that path here. Prints run status, per-step status/errors, and the
# resolved inputs/outputs of each step (record counts, resolved recordId/field/value)
# so you can confirm variables resolved to real values, not empty strings.
#
# Requires: jq. Handles both {data:[{...}]} and a bare run object.

set -euo pipefail
F="${1:?usage: inspect_run.sh <run-json-file>}"

# Normalize to the run object whether wrapped in {data:[...]} or not.
RUN='if (.data|type=="array") then .data[0] else . end'

echo "=== run status ==="
jq -r "($RUN) | \"\(.status)  \(.error // \"\")\"" "$F"

echo "=== steps (id / type / status / error) ==="
jq -r "($RUN) | .steps[] | \"\(.stepId)\t\(.stepType)\t\(.status)\t\(.error // \"\")\"" "$F"

echo "=== findRecords counts ==="
jq -r "($RUN) | .steps[] | select(.stepType==\"findRecords\") | \"\(.stepId): count=\(.outputs.count // \"?\")\"" "$F"

echo "=== findRecords resolved filter values (spot silent-empty / wrong shape) ==="
jq -c "($RUN) | .steps[] | select(.stepType==\"findRecords\") | {step:.stepId, aiFindPrompt:(.inputs.aiFindPrompt // null), filterValue:(.inputs.filter.value // null)}" "$F" 2>/dev/null || true

echo "=== Salesforce writes (recordId / field / value / dryRun) ==="
jq -c "($RUN) | .steps[] | select(.stepType==\"updateSalesforce\" or .stepType==\"createSalesforce\") | {step:.stepId, iter:(.iterationPath // null), recordId:(.outputs.recordId // .inputs.recordId // null), field:(.outputs.field // null), value:(.outputs.value // null), dryRun:(.outputs.dryRun // null), error:(.error // null)}" "$F"

echo "=== agent outputs (truncated) ==="
jq -r "($RUN) | .steps[] | select(.stepType==\"runAgent\") | \"\(.stepId): \(.outputs.output // \"\" | .[0:300])\"" "$F" 2>/dev/null || true

echo
echo "Checklist: valid case -> status=completed, count>0, real recordIds, non-empty values."
echo "           empty [] values or empty recordId => a {{...}} ref resolved to nothing."
