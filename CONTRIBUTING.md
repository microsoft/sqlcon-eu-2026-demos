# Contributing

Keep each demo self-contained so contributors can work without moving or rewriting another
presenter's files.

## Folder conventions

- Add a keynote demo as a new top-level folder with a descriptive name.
- Keep its application, database scripts, setup, assets, and presenter notes inside that
  folder.
- Put code in `shared/` only after two demos use it.
- Do not rename another demo's folder without coordinating with its owner.
- Keep transcripts and event-level source material under `corenote/`.

## Publication rules

- Do not commit credentials, tokens, connection profiles, local absolute paths, or private
  customer data.
- Do not commit recordings, virtual environments, dependency folders, or generated build
  output.
- Use placeholders in sample environment files.
- Gate destructive or expensive database scripts behind an explicit approval variable.
- Back every spoken performance or scale claim with a retained report.

## Validation

Run the build and lint commands documented by the demo you changed. For T-SQL, run the
repository's SQL analyzer or review the script against the applicable T-SQL guidance.