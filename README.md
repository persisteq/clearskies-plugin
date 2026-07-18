# clearskies

Bring the revenue context already connected to clearskies into Claude or ChatGPT (Codex). Research
accounts and deals, prepare for meetings, find evidence across customer interactions, and build
reliable RevOps workflows without switching between systems.

Depending on your clearskies connections and sync settings, available context can include CRM
records, meetings, call transcripts, email, Slack threads, support tickets, and GitHub activity.

## Get started

### 1. Install the plugin

#### Claude

1. In Claude, go to **Customize** and select **Plugins**.
2. Click **Add**.
3. Select **Add marketplace**.
4. Paste this repository:

```text
github.com/persisteq/clearskies-plugin
```

5. Open **clearskies** from the new marketplace and install it.

#### ChatGPT (Codex)

1. In ChatGPT, open the **Plugins** page.
2. Click the arrow next to **Create**.
3. Select **Add marketplace**.
4. Paste this repository:

```text
github.com/persisteq/clearskies-plugin
```

5. Open **clearskies** from the new marketplace and install it.

Claude or ChatGPT will prompt you to connect clearskies when authentication is needed. The plugin
does not store your credentials.

### 2. Ask a revenue question

You can ask naturally. For example:

- “Brief me on Acme using the CRM, recent calls, and email.”
- “What changed in this deal over the last 30 days?”
- “Summarize the objections and next steps from our recent customer conversations.”
- “Show my open pipeline closing this quarter and flag deals without recent activity.”
- “Prepare me for tomorrow's meetings with account history and open opportunities.”
- “Build a workflow that posts a Slack summary after customer calls.”
- “Keep the Opportunity Next Steps field updated from relevant meetings.”

## Available skills

| Skill | Use it for |
| --- | --- |
| [`use-clearskies-revenue-data`](skills/use-clearskies-revenue-data/SKILL.md) | Account research, pipeline questions, meeting preparation and recaps, and finding evidence across CRM and customer interactions. |
| [`clearskies-workflow-builder`](skills/clearskies-workflow-builder/SKILL.md) | Creating, changing, testing, troubleshooting, and publishing revenue workflows. |
| [`ai-update-salesforce-field`](skills/ai-update-salesforce-field/SKILL.md) | Keeping a chosen Salesforce field up to date from relevant meeting content. |

You do not need to remember skill names—describe the outcome you want and Claude or ChatGPT will use
the appropriate skill. The explicit names are useful when you want to invoke one directly.

## Common RevOps use cases

### Account and deal research

Combine current CRM state with recent meetings, calls, and email to understand account history,
deal movement, stakeholders, risks, objections, and next steps.

### Meeting preparation and follow-up

Create a concise briefing before a customer meeting, recap what happened afterward, and identify
follow-up actions grounded in the conversation and CRM.

### Pipeline inspection

Review pipeline by owner, stage, close date, amount, or other synchronized fields. Find stale deals,
missing activity, and changes that deserve attention.

### Conversation and customer evidence

Search synchronized interactions for themes such as objections, product feedback, competitive
mentions, commitments, or buying signals, then connect that evidence back to CRM records.

### Revenue workflows

Build and test automations triggered by calls, schedules, or CRM changes. Workflows can find records,
run AI analysis, send Slack or email updates, and write approved changes back to Salesforce.

### CRM hygiene

Use AI to maintain a selected Salesforce field from relevant meeting content—for example, Next
Steps, Risks, or an onboarding status field.

## Working safely

- Results reflect the systems, objects, fields, and history your team has chosen to synchronize.
  “Not found” may mean the information is not synchronized, not that it does not exist in the
  source system.
- clearskies reads only the customer-interaction content needed to answer the question you asked.
- Workflow changes are drafted, validated, and tested before publication. A live workflow is never
  published or edited without your explicit approval.
