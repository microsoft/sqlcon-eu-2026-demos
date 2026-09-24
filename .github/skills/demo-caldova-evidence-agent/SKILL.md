---
name: demo-caldova-evidence-agent
description: "Guide or rehearse the Caldova Evidence Agent demo one beat at a time. Use when: demo the Caldova evidence agent, rehearse the SQL MCP demo, walk through the evidence agent, start the evidence demo, next beat, show Foundry Log stream, or practice the causal evidence follow-up."
---

# Demo Caldova Evidence Agent

Guide the presenter from `DEMO-RUNBOOK.md`. Do not provision, redeploy, or modify resources during a demo request.

## Preflight

1. Read `DEMO-RUNBOOK.md` completely.
2. Run `deploy/11-verify-system.ps1` synchronously.
3. Follow the `run-caldova-evidence-agent` skill to open or reuse the app and verify its standalone Edge window.
4. Ask the presenter to open the hosted agent Log stream in Microsoft Foundry if it is not already visible.
5. Report readiness and wait for the presenter to say `start`.

## Beat Order

Guide exactly one beat at a time:

1. Establish the natural research question.
2. Show the live Foundry skill and three direct SQL MCP calls.
3. Read the five-phase visual briefing.
4. Use **Find strongest causal evidence** and show the visual comparison.
5. Close on the governed three-tool SQL MCP boundary.

After each beat, provide only the action, expected visual proof, and concise talk track. Wait for `next` before advancing.

## Guardrails

- Never run deployment scripts during a presentation walkthrough.
- Never reset the database or corpus during the demo.
- Do not claim the human clinical evidence is high-confidence; say confidence is high for mechanistic plausibility and qualified for human causality.
- The causal follow-up should reuse evidence and make no new MCP search when the existing sources are sufficient.
