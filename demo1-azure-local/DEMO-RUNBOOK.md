# Caldova Regional Care Demo Runbook

## Preflight

Complete preflight before the presentation. Do not provision or repair the
environment on stage.

- The Regional Care Transfer Center is running at `http://localhost:5099`.
- `http://localhost:5099/api/health` reports `Healthy` for
  `CaldovaRegionalCare`.
- The Azure portal is signed in and the Azure Local VM, AKS cluster, and Azure
  Virtual Desktop resources are ready to show.
- VS Code is open with the public demo workspace and MSSQL extension.
- The MSSQL extension is connected to `localhost`, database
  `CaldovaRegionalCare`.
- Phi-3.5 Mini from Foundry Local is available in VS Code for the final chat.
- All displayed patient and transfer records are synthetic.

## Locked demo order

### 1. Application

**Say:** "This is Caldova's Regional Care Transfer Center. It coordinates
incoming emergency transfers using operational and clinical data held in SQL
Server."

**Show:**

1. Open `http://localhost:5099`.
2. Show the live incoming-transfer queue and select a transfer.
3. Point out the field narrative, extracted signals, destination, ETA, and the
   receiving briefing with its grounding sources.
4. Generate a receiving briefing only if a fresh invocation is part of this
   rehearsal; the action calls the real database workflow.

**Land:** "The application is thin. SQL Server owns the data, grounding packet,
approved skill, model invocation, and persisted result."

### 2. Azure portal: Azure Local VM, AKS, and Azure Virtual Desktop

**Say:** "The application, SQL data, and model inference run in Caldova's
organization-controlled Regional Care environment on connected Azure Local."

**Show in the Azure portal:**

1. The Azure Local VM hosting the application and SQL Server.
2. The AKS cluster hosting the Foundry Local model deployment.
3. The Azure Virtual Desktop resource used to enter the demo environment.

Do not describe this connected lab as disconnected Azure Local. Do not change,
restart, scale, or redeploy portal resources during the presentation.

**Land:** "Azure supplies connected management and Arc governance while this
workload remains inside the Regional Care environment."

### 3. VS Code: MSSQL connection and database scripts

**Say:** "Now we can inspect the same workflow as a database developer."

**Show:**

1. VS Code with the public demo workspace.
2. The MSSQL extension connected to `localhost` / `CaldovaRegionalCare`.
3. The ordered scripts in `database/`.
4. Point out `01-schema.sql`, `03-programmability.sql`, and
   `06-skill-invocation.sql` as the files that own the AI contract.

**Land:** "The schema, data contracts, and programmability are versioned as
repeatable SQL deployment scripts."

### 4. Native RegEx extraction

Open:

`database/03-programmability.sql`

**Show:**

1. The field narrative selected for the transfer.
2. Active rules read from `ai.SignalRule`.
3. `CROSS APPLY REGEXP_MATCHES(n.NarrativeText, r.Pattern, r.Flags)`.
4. The named matches persisted in `ai.ExtractedSignal`.

**Say:** "SQL Server 2025 turns useful details in the unstructured field note
into governed, queryable signals. This is extraction, not model inference."

**Land:** "Regular expressions give us deterministic signals before anything is
sent to the model."

### 5. Approved ai.Skill table

Open:

`database/01-schema.sql`

In the MSSQL extension, show the approved row without exposing unrelated secret
material:

```sql
SELECT
    SkillName,
    SkillVersion,
    IsApproved,
    IsActive,
    JSON_VALUE(SkillJson, '$.purpose') AS Purpose,
    SkillJson
FROM ai.Skill;
```

**Say:** "The prompt contract is data. It is named, versioned, hashed, approved,
and activated independently of application code."

Point out `ReceivingBriefing` version `1.0`, its purpose, constraints, and output
contract.

**Land:** "The application cannot invent a prompt; it requests an approved skill
by name and version."

### 6. Transfer skill procedure: JSON payload and sp_invoke

Open:

`database/06-skill-invocation.sql`

In the MSSQL extension, show the Foundry Local URL without selecting credential
material:

```sql
SELECT
   EndpointName,
   BaseUrl + N'/v1/chat/completions' AS ChatCompletionUrl,
   ModelId,
   IsActive
FROM ai.ModelEndpoint
WHERE EndpointName = N'FoundryLocalOnAzureLocal';
```

Point out the active endpoint:
`https://172.25.29.251/phi-35-mini/v1/chat/completions`.

Walk through the procedure in this order:

1. Read only an approved, active skill from `ai.Skill`.
2. Read the immutable `PacketJson` from `ai.TransferPacket`.
3. Build the system and user messages with `FOR JSON PATH`.
4. Embed messages with `JSON_QUERY` and build `@RequestJson`, the OpenAI-format
   payload containing `model`, `messages`, `temperature`, and `max_tokens`.
5. Persist the exact skill and request in `ai.ModelInvocation` before the call.
6. Show both `sys.sp_invoke_external_rest_endpoint` branches: credentialless for
   the legacy local runtime and `@credential = @CredentialName` for the
   authenticated Azure Local Gateway.
7. Parse the HTTP status with `JSON_VALUE`, parse assistant content with
   `OPENJSON`, enforce valid JSON and the skill output contract, then persist the
   briefing and its seven grounding sources.

**Say:** "The payload combines authoritative skill instructions with a grounded
transfer packet. SQL Server sends that JSON to Phi-3.5 Mini and validates the
JSON response before the application can use it."

Never display the API key, database scoped credential secret, kubeconfig, or
database master-key password.

**Land:** "The model summarizes; SQL Server controls what it sees, records the
invocation, validates the response, and preserves provenance."

### 7. Phi-3.5 Mini in VS Code Chat

**Say:** "The same Foundry Local model is also available directly to the
developer inside VS Code."

**Show:**

1. Open the VS Code chat experience.
2. Select Phi-3.5 Mini from Foundry Local.
3. Start a new Ask chat and confirm the selected model without submitting a
   clinical prompt.

Do not improvise a clinical diagnosis, prescription, or treatment prompt. This
beat demonstrates that the same local model is available to the developer.

**Land:** "The local model supports both the governed database workflow and the
developer experience inside the same Regional Care boundary."

## Close

"The application runs here. The patient data stays here. The model runs here.
And Azure still gives Caldova one place to govern it."
