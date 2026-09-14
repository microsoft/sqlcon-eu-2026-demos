# Demo 2 stage script

**Target length:** 1:50 to 2:00
**Thesis:** Start small. Scale without re-architecting.

## Preflight

- Open the app and confirm `4K`, `1M`, and `Named Replica` report `Live ready`.
- Run the stage question once on `4K` and `1M` so both plans are warm.
- Leave the Evidence tab selected.
- Speak only latency numbers that appear in a retained report.

## Live script

**0:00 | SQL query tab visible**

"Start small. Scale without re-architecting.

This is Caldova, a biomedical evidence explorer. Underneath it is one parameterized Azure
SQL query. Five hundred twelve dimension embeddings, compared with cosine distance. This
application contract stays steady as the database target changes."

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

**1:05 | Select 1M**

"Now the same application against one million passages on the primary. The embedding model,
vector dimensions, cosine distance, and result contract stay the same. This path uses the
existing DiskANN index on the one-million-row table.

The row count and vector-search time on screen come from that database, not from the pilot."

**1:30 | Select Named Replica**

"For read scale-out, I can send the same search to a named replica. It shares the primary's
storage and the same one-million-row vector index, while its compute is independent. There
is no second copy of the data and no second index to build."

**1:50**

"Start small. Scale without re-architecting."

The `1B` button is an optional honesty check: it reports that the vector index has not been
built and leaves the timing blank. Do not describe it as a working search target.

## If something fails

Do not repair on stage. Say:

"The live contract gate did not pass, so Caldova is deliberately withholding database
timings rather than showing a number it cannot verify."

Then skip every statement containing a timing, a row count, or a comparison, and close with
the thesis.
