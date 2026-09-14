# Demo 2 stage script

**Target length:** 1:50 to 2:00
**Optional named-replica extension:** 20 seconds
**Thesis:** Start small. Grow big. Keep the application contract steady.

## Preflight

- Open the app and confirm `4K`, `1M`, and `Named Replica` report `Live ready`.
- Confirm `1B` reports that its vector index has not been built and shows no latency.
- Run the stage question once on `4K` and `1M` so both plans are warm.
- Leave `4K`, `Hybrid`, and the Evidence tab selected.
- Speak only latency numbers that appear in a retained report.

## Live script

**0:00 | SQL query tab visible**

"This is Caldova, a biomedical evidence explorer on Azure SQL Hyperscale. Every article is
split into passages and embedded, with a vector index over the corpus. One search contract
sits underneath the app, and it stays steady as the database grows."

**0:22 | Evidence tab, run the stage question**

"Let's ask it something real. How does disruption of the intestinal microbiome influence
anxiety and depressive symptoms?

That isn't a keyword match. The meaning is what gets searched, and every answer links back
to its article."

**0:42 | Expand a result, then show the SQL query**

"Each result includes the surrounding passages, so the quote reads in context.

This is hybrid: vector search finds meaning, keyword search finds exact strings such as
gene names or drug codes, and SQL fuses the rankings. Filters run inside vector search, and
the timing shown is measured inside the engine."

**1:08 | Return to Evidence, keep 4K selected**

"This 4K pilot is Hyperscale serverless. It scales down to half a vCore and auto-pauses when
idle, so I don't pay for compute when the app isn't used."

**1:23 | Select 1M and run the same question**

"Now the same application against one million passages on the primary. The embedding model,
vector dimensions, distance metric, and result contract stay fixed. This path uses the
existing DiskANN index on the one-million-row table."

**1:40 | Select 1B**

"The full table has crossed one billion passages. Its vector index has not been built, and
the application says so instead of presenting a latency it cannot verify. The one-million-
row target is the live scale comparison in this demo."

**1:55 | Close**

"Start small. Grow big. Keep the contract steady while the data grows. You shouldn't have
to rebuild your app just because your corpus did. That's Hyperscale."

## Optional named-replica extension

**2:00 | Select Named Replica and run the same question**

"For read scale-out, I can send the same search to a named replica. It shares the primary's
page servers and the same one-million-row vector index, so there is no data copy and no
second index to build. Its compute is sized independently, so work on the primary does not
compete with my search queries."

## If something fails

Do not repair on stage. Say:

"The live contract gate did not pass, so Caldova is deliberately withholding database
timings rather than showing a number it cannot verify."

Then skip every statement containing a timing, a row count, or a comparison, and close with
the thesis.
