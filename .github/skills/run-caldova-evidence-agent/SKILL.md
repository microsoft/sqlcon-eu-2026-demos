---
name: run-caldova-evidence-agent
description: "Start, open, verify, or stop the Caldova Evidence Agent application. Use when: run the Caldova evidence app, start the evidence agent, open the research app, check the app, verify the live app, or stop the local app."
---

# Run Caldova Evidence Agent

## Start

1. Read `README.md` Run Locally section.
2. Run `run.ps1` synchronously. The script resolves the hosted agent from explicit environment variables, local `azd` state, or deployed App Service settings; then it builds the app, starts Express, probes readiness, and opens a standalone Microsoft Edge app window.
3. Verify `http://127.0.0.1:8000/api/agent/readiness` reports `configured: true` and the expected hosted-agent version.
4. Confirm the script detected a visible Edge window titled `Caldova`.
5. Report the local URL and version.

## Verify Deployed App

Run `deploy/11-verify-system.ps1` synchronously. It exercises the natural initial prompt and guided causal follow-up through App Service.

## Stop

Run `stop.ps1` synchronously. Confirm the recorded process is no longer running.

## Guardrails

- Starting a server is not enough: the actual standalone Edge window must open.
- Do not use VS Code Simple Browser for the presenter experience.
- Do not redeploy Azure resources for a run-only request.
- If automatic resolution fails, ask for `CALDOVA_AGENT_ENDPOINT` and `CALDOVA_AGENT_VERSION`; do not guess either value.
- If the app reports a stale agent version, verify App Service settings and recycle the worker before changing code.
