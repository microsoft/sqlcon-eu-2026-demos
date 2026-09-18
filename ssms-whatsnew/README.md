# SSMS What's New Demo

> Public setup and presenter materials for the SQLCon EU corenote SSMS demo.

## Recorded Story

Version 1 was recorded in a Windows virtual machine with SSMS 22.10.2 against a disposable Azure SQL database. Those choices are not requirements. You can reproduce the workflow with any supported Windows environment and either SQL Server or Azure SQL Database.

The story starts with a poorly formatted WideWorldImporters query from a coworker. The presenter formats it, runs it with an actual execution plan, enlarges the results grid, and asks GitHub Copilot Agent Mode for the most important performance improvement.

Start with the [environment setup and rehearsal guide](setup/README.md), then follow the [Version 1 storyboard](demo/version-1-from-problem-to-answer.md).

## Package Structure

```text
ssms-whatsnew/
├── README.md
├── setup/
│   └── README.md
├── presenter/
├── demo/
└── assets/
    ├── README.md
    ├── version-1/
    │   └── setup, demo, validation, reference, and teardown SQL
    └── version-2/
        └── validation, results, and formatter SQL
```

## File Index

| File | Audience | Purpose | Status |
| --- | --- | --- | --- |
| [Setup guide](setup/README.md) | Anyone reproducing the demo | Prepare SSMS and a disposable WideWorldImporters database | Ready |
| [Demo options](presenter/story-recommendation.md) | Presenter and event team | Compare the two proposed two-minute demo versions | Initial concepts drafted |
| [Version 1: From Problem to Answer](demo/version-1-from-problem-to-answer.md) | Presenter and demo operator | Reproduce the recorded workflow, timing, positioning, and fallback | Recorded |
| [Version 2: Five Customer Asks We Delivered](demo/version-2-five-customer-asks.md) | Presenter and demo operator | Define the rapid-fire feature reel, timing, positioning, and open decisions | Initial concept drafted |
| [Assets index](assets/README.md) | Presenter and demo operator | Access the versioned setup, query, validation, and teardown scripts | Ready |

## Working Conventions

- Use a disposable or approved sample database.
- Do not commit credentials, access tokens, connection profiles, or personal Azure resource details.
- Validate the result set and plan shape in the environment used for the presentation.
- Keep recordings and other large binaries outside the repository.
