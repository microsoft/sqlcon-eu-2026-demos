# Demo 2 stage script

**Target length:** 1:50 to 2:00
**Thesis:** Start small. Scale without re-architecting.

## Preflight

- Open the app and confirm the Pilot database reports `Live ready`.
- Run the stage question once so the plan is warm.
- Leave the Evidence tab selected.
- Speak only latency numbers that appear in a retained report.

## Live script

**0:00 | SQL query tab visible**

"Start small. Scale without re-architecting.

This is Caldova, a biomedical evidence explorer. Underneath it is one parameterized Azure
SQL query. Five hundred twelve dimension embeddings, compared with cosine distance. This
statement stays the same for both databases."

**0:20 | Evidence tab, run the stage question**

"Let's ask it something real. How does disruption of the intestinal microbiome influence
anxiety and depressive symptoms?

Nothing in that sentence is a keyword match. The query is embedded with the same model that
embedded the corpus, and every answer comes back tied to the article it came from."

**0:45 | Switch search mode**

"I can run this three ways. Vector on its own, keyword on its own, or hybrid, which fuses
both rankings. Keyword still wins on rare clinical terms, so in practice we run them
together. And each result carries the passages either side of it, so the quote reads as
written."

**1:05 | Select Research**

"Now the same application against the independent research database. I'm not changing the
query, the embedding model, or the schema. Only the connection target.

That corpus is still loading embeddings, so its vector index has not been built yet. The
app says not ready and leaves the timings blank rather than showing a number it cannot
verify."

**1:30 | Return to Evidence**

"That is the operating model: begin with the footprint you need, keep the contract steady
as the corpus grows, and scale without rebuilding the application around a different data
system."

**1:50**

"Start small. Scale without re-architecting."

## If something fails

Do not repair on stage. Say:

"The live contract gate did not pass, so Caldova is deliberately withholding database
timings rather than showing a number it cannot verify."

Then skip every statement containing a timing, a row count, or a comparison, and close with
the thesis.
