# Demo 2 recording

**Length:** about 2:42 · **Output:** `recording/caldova-demo2.mp4`
**Voice:** Samantha, rate 145 (`--voice` / `--rate` to change)
**Thesis:** Start small. Scale without re-architecting.

Rebuild:

```bash
node recording/capture_app_frames.mjs      # live app frames
python recording/render_azure_frames.py    # Azure config and monitoring frames
python recording/build_recording.py        # narration and assembly
```

Every number in the Azure frames is read from Azure Resource Manager, Azure Monitor, or
`sys.partitions` at capture time. The narration assumes every beat has a working visual
behind it, so a beat that cannot be captured is a demo gap to close, not a line to hedge.

## Beats

| # | Frame | Shows |
|---|---|---|
| 1 | `frame1.png` | The SQL statement and the vector index |
| 2 | `frame2.png` | Hybrid result for a natural-language question |
| 3 | `frame3.png` | Context expansion around the quoted passage |
| 4 | `frame4.png` | Cut back to the query, its fusion and its filter predicate |
| 5 | `portal1.png` | Serverless configuration and auto-pause |
| 6 | `portal2.png` | Monitoring, intermittent activity |
| 7 | `frame5.png` | The same search at scale, with the rows searched |
| 8 | `portal3.png` | Large database vCores and storage |
| 9 | `portal4.png` | Corpus row count past a billion passages |
| 10 | `frame6.png` | Named replica serving the read-only search workload |
| 11 | `frame7.png` | Close |

Beats 1 through 4 all run on hybrid, the app default, so one result set carries the whole
opening and beat 4 explains what is already on screen instead of re-running the search.

Beats 1, 7, 9, and 10 depend on visuals the app must show explicitly: the vector index,
the number of rows each search runs across in both the small and large targets, and the
named replica serving the query.

## Narration

**1.** Let's look at how you can start small and scale without re-architecting with Azure SQL Hyperscale. This is Caldova, a biomedical evidence explorer, and it runs on Hyperscale. Every article is chunked into passages,
every passage is embedded, and a vector index sits over all of them. Underneath the whole
app there is one SQL query, and that query doesn't change when the database does.

**2.** Let's ask it something real. How does disruption of the intestinal microbiome
influence anxiety and depressive symptoms? Nothing in that sentence is a keyword match. The
meaning is what gets searched, and every answer comes back tied to the article it came
from.

**3.** Each result brings the passages either side of it, so the quote actually reads in
context instead of stopping mid-sentence.

**4.** So how did that actually run? Three ways to search, and this was hybrid. Vector
search finds meaning. Keyword search finds the exact string, which is what you want for a
gene name or a drug code, the rare terms embeddings tend to blur. Hybrid runs both and
fuses the two rankings together, which is why those results had the concept matches and the
precise ones. And because this is all just SQL, the filter goes inside the search. There's
one right there, dropping boilerplate sections before they ever compete for a slot.
Journal, publication date, study type, anything in the row next to the vector works the
same way. SQL applies those predicates during the vector search instead of after it, so a
narrow filter still comes back full of good matches rather than quietly dropping them. And
that timing is the vector search itself, measured inside the engine.

**5.** Here's the part I like. This is Hyperscale serverless. It scales down to half a
vCore, and when nobody is searching, it pauses. If the app isn't being used, I'm not paying
for compute. The next question brings it straight back.

**6.** And this is what real usage looks like. Short bursts, long quiet gaps. Those flat
stretches are the whole point, because the quiet time costs me nothing.

**7.** Now the scenario moves on. The research grew. Same app, same query, same schema,
same vector index definition. I just point it at the production corpus, and look at how
many rows the search is now running across.

**8.** That database is a different animal. A hundred and ninety-two vCores and almost five
terabytes, next to the pilot's two.

**9.** It's past a billion passages across millions of articles, and it's still growing.
The vector index never had to be rebuilt to get here. Same index, same query, just far more
rows behind it.

**10.** And because search is read only, I can keep it completely separate with a
Hyperscale named replica. This is read scale-out on the fly. It uses the same page servers
as the primary, so there's no data copy, and it comes up in about a minute. It gets its own
compute, sized independently, so the ingestion workload on the primary never feels my
queries. You can run up to thirty of them.

**11.** Start small. Keep the contract steady while the data grows. You shouldn't have to
rebuild your app just because your corpus did. That's Hyperscale. Start small, and scale
without re-architecting.

### Sources for beat 4

The filtering claim is the documented behavior of `VECTOR_SEARCH`, which lists
**iterative filtering**: "Predicates in the WHERE clause are applied during the vector
search process, not after retrieval."

- [VECTOR_SEARCH (Transact-SQL)](https://learn.microsoft.com/sql/t-sql/functions/vector-search-transact-sql?view=sql-server-ver17)

### Sources for beat 10

Every named-replica claim above is taken from the product documentation:

- Same page servers, no data copy, independent service level objective, primary unaffected,
  read-only, up to 30 replicas:
  [Hyperscale secondary replicas](https://learn.microsoft.com/azure/azure-sql/database/service-tier-hyperscale-replicas?view=azuresql#named-replica)
- Created in about a minute because no data movement is involved:
  [Configure a Hyperscale named replica](https://learn.microsoft.com/azure/azure-sql/database/hyperscale-named-replica-configure?view=azuresql#create-a-hyperscale-named-replica)

## Voice

No Premium voices are installed on the build machine, so the built-in `say` voices are the
ceiling. Compare them in `recording/audio/samples/voice-comparison.m4a` and rebuild with
whichever you prefer. Installing an enhanced English (US) voice through
**System Settings → Accessibility → Spoken Content → Manage Voices** is a much larger
improvement than any tuning here.

## Portal captures

The Azure beats are rendered from live API reads because the portal needs an interactive
sign-in. To swap in real captures, record these and replace `portal1.png`–`portal4.png`
at 2880×1800:

- `research` compute and storage (private stamp):
  `https://portal.azure.com/?feature.customportal=false&feature.canmodifystamps=true&SqlAzureExtension=flight36#resource/subscriptions/fa58cf66-caaf-4ba9-875d-f310d3694845/resourceGroups/antho-rg/providers/Microsoft.Sql/servers/antho-caldova/databases/research/configure`
- `research` monitoring: same resource, `/performance`
- `vbench_large` overview:
  `https://ms.portal.azure.com/#@microsoft.onmicrosoft.com/resource/subscriptions/44fefc06-f7c7-4326-9471-1852e148b8bb/resourceGroups/vector-benchmark/providers/Microsoft.Sql/servers/vbnech-large-server/databases/vbench_large/overview`
