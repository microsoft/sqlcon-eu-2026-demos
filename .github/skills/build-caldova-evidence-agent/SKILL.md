---
name: build-caldova-evidence-agent
description: "Build, provision, repair, or verify the Caldova Evidence Agent stack. Use when: build the Caldova evidence agent, deploy the evidence demo, provision SQL MCP, create the hosted agent, publish the evidence skill, deploy the app, rebuild the demo, or verify the complete environment."
---

# Build Caldova Evidence Agent

Use the repository's staged scripts as the source of truth. Do not recreate resources with ad hoc commands when a canonical script exists.

## Workflow

1. Read `README.md`, especially Prerequisites, Portable Configuration, and Security Boundary.
2. Establish fresh state with `az account show`; do not infer subscription or deployment health from terminal history.
3. Confirm the target subscription, tenant, regions, resource group, and naming suffix from environment variables or the defaults resolved by `deploy/00-config.ps1`.
4. Run `deploy/01-preflight.ps1` synchronously. It is read-only.
5. Before creating billable resources, show the resolved target and ask for plain-text approval.
6. For a complete build, run `deploy/Build-All.ps1` synchronously with no timeout.
7. For repair, start at the earliest failed numbered stage and continue through `deploy/11-verify-system.ps1`.
8. Report the App Service URL, hosted-agent version, skill version, SQL MCP endpoint, and verification results.

## Guardrails

- Never run `azd ai agent init`; the hosted project is already scaffolded.
- Never copy `.env`, `.azure`, `.checkpoints`, `bin`, `obj`, `dist`, or `node_modules` into source control.
- Treat `deploy/01-preflight.ps1` as the subscription and quota gate.
- Do not weaken the three-tool SQL MCP boundary.
- Do not expose secrets or access tokens in output.
- Do not delete or recreate the resource group unless explicitly requested.
