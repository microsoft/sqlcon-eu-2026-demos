# Demo 2 recording

**Length:** about 2:26 · **Output:** `recording/caldova-demo2.mp4`
**Voice:** Samantha, rate 145 (`--voice` / `--rate` to change)
**Thesis:** Start small. Scale without re-architecting.

Rebuild:

```bash
node recording/capture_app_frames.mjs      # live app frames
python recording/render_azure_frames.py    # Azure config and monitoring frames
python recording/build_recording.py        # narration and assembly
```

Every number in the Azure frames is read from Azure Resource Manager, Azure Monitor, or
`sys.partitions` at capture time. Where a visual does not exist yet, the narrator says so
rather than implying it is on screen.

## Beats

| # | Frame | Shows |
|---|---|---|
| 1 | `frame1.png` | The SQL statement |
| 2 | `frame2.png` | Semantic result for a natural-language question |
| 3 | `frame3.png` | Vector / keyword / hybrid modes and context expansion |
| 4 | `portal1.png` | Serverless configuration and auto-pause |
| 5 | `portal2.png` | Monitoring, intermittent activity |
| 6 | `frame4.png` | Research target reporting not ready |
| 7 | `portal3.png` | Large database vCores and storage |
| 8 | `portal4.png` | Corpus row count, still loading |
| 9 | `frame5.png` | The same statement on the larger database |
| 10 | `frame6.png` | The operating model |
| 11 | `frame7.png` | Close |

## Narration

**1.** Start small. Scale without re-architecting. This is Caldova. It's a biomedical
evidence explorer, and underneath it there's just one SQL query. Five hundred twelve
dimension embeddings, compared with cosine distance. That query doesn't change when the
database does.

**2.** Let's ask it something real. How does disruption of the intestinal microbiome
influence anxiety and depressive symptoms? Nothing in that sentence is a keyword match. The
embeddings do the work, and every answer comes back tied to the article it came from.

**3.** You can switch how it searches. Vector on its own, keyword on its own, or hybrid,
which fuses both. Keyword still wins on rare terms, so we run them together. And each
result brings the passages either side of it, so the quote actually reads.

**4.** Here's the part I like. This is Hyperscale serverless. It scales down to half a
vCore, and after an hour of nobody asking it anything, it pauses and you stop paying for
compute. The next query wakes it back up.

**5.** And this is what the usage actually looks like. Short bursts, long quiet gaps. Those
flat stretches are the whole point. I have a job hitting it every three hours, so we can
watch it pause and resume for real.

**6.** Now watch what happens when I point the same app at the big database. Same query,
same vectors, same schema. Only the connection changes. Right now it says not ready, and
the timings are blank on purpose. The index isn't built yet, so Caldova won't show you a
number it can't back up.

**7.** That database is a different animal. A hundred and ninety-two vCores and almost five
terabytes, next to the pilot's two.

**8.** Its corpus is already past three hundred million passages, and it grows while you
watch. The team is still loading embeddings on the way to a billion rows. That's why
there's no vector index on it yet.

**9.** When it is ready, the same query runs there too. Same statement, same embedding
model, same index. Only the connection string changes.

**10.** So that's the idea. Start with the smallest thing that works. Keep the contract
steady while the data grows. You shouldn't have to rebuild your app just because your
corpus did.

**11.** Start small. Scale without re-architecting.

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
