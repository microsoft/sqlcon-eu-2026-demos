<!-- MACHINE-OPTIMIZED -->
# SQLCon Barcelona: Two-Minute SSMS Demo Options

> Comparison of two developed demo options for the SQLCon Barcelona corenote, EBCs, field events, and the public corenote GitHub repository.

## Shared Goal

Show how SSMS has evolved in response to customer needs over the past 6-12 months. Keep each option:

- At or under two minutes.
- Easy for another presenter to run.
- Reusable for EBCs and field events.
- Safe to publish in the corenote GitHub repository.
- Focused on SSMS; migration is covered separately.
- Built for SSMS 22.10.2.
- Backed by reproducible WideWorldImporters SQL assets.

## Options

| Version | Story | Shape | Status |
| --- | --- | --- | --- |
| [Version 1](../demo/version-1-from-problem-to-answer.md) | "A coworker sent me this SQL" | Connect through a custom favorite, format the coworker's query, run it, inspect the separate execution-plan tab, zoom the results grid, then ask Agent Mode to optimize it | Detailed live-demo draft with SQL assets |
| [Version 2](../demo/version-2-five-customer-asks.md) | Five Customer Asks We Delivered | Recorded rapid-fire reel: connection management, Group by Schema, results export formats, SQL Formatter, and Agent Mode | Detailed recording draft with SQL assets |

## Option Comparison

| Dimension | Version 1: Coworker SQL | Version 2: Five Customer Asks |
| --- | --- | --- |
| Primary strength | One relatable, coherent story | Maximum feature breadth |
| Opening hook | "A coworker sent me this SQL." | "You asked us to make the everyday SSMS experience better." |
| Connection moment | Horizontal Modern connection dialog with custom-named favorite | Saved connections, search/filter, and import/export |
| Object Explorer moment | **Group by Schema** shown ambiently without browsing | **Group by Schema** toggled as a feature reveal |
| Results moment | Separate execution-plan tab plus results-grid zoom | Excel, JSON, Markdown, and XML export formats |
| Formatter role | Makes the coworker's SQL readable before analysis | Standalone rapid-fire before-and-after |
| Agent Mode role | Analyzes the active query and recommends performance improvements | Explains the active query and suggests a way to validate performance |
| Production model | Live path with an immediate screenshot fallback | Recorded demo |
| Timing risk | Agent response may push runtime toward 2:30 | Many transitions must fit into two minutes |
| Best use | Corenote narrative and technical walkthroughs | ICYMI reel, EBCs, field events, and modular reuse |

## Evaluation Criteria

Use these questions to compare the two versions:

| Criterion | Question |
| --- | --- |
| Story clarity | Can the audience follow the problem and outcome without narration-heavy setup? |
| Customer relevance | Does the flow reflect recognizable SQL professional work? |
| Feature proof | Are the new capabilities visible rather than merely mentioned? |
| Applause potential | Is there one memorable payoff? |
| Production fit | Does the live or recorded format fit the corenote production plan? |
| Reusability | Can another presenter reproduce it from the public instructions? |
| Timing | Does Version 1 have an acceptable Agent Mode fallback, and does Version 2 record cleanly at two minutes? |

## Shared Positioning

- Frame the work as **customer-driven improvements** unless exact vote data supports a stronger claim.
- Label preview features clearly.
- Use the approved event language for GitHub Copilot Agent Mode GA.
- Do not make unapproved availability, roadmap, security, or performance claims.
- Use the public WideWorldImporters sample database and public-safe connection names.
- Use the versioned scripts in the [assets index](../assets/README.md).

## Handoff Decision

Both options now include:

- Demoer context and prerequisites.
- A timed storyboard.
- Step-by-step instructions.
- Copy-ready Agent Mode prompts.
- Versioned SQL setup, validation, query, reference, and teardown assets where applicable.
- Resolved decisions, remaining open decisions, and next-detail work.

Select the primary option after timing Version 1's live Agent Mode path and recording a full two-minute take of Version 2. Keep the other version as the alternate and as reusable EBC/field material.
