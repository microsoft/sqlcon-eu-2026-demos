#!/usr/bin/env python3
"""Build the Caldova demo recording from narration segments and captured frames."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent
FRAMES = ROOT / "frames"
AUDIO = ROOT / "audio"
BUILD = ROOT / "build"
OUTPUT = ROOT / "caldova-demo2.mp4"

DEFAULT_VOICE = "Samantha"
DEFAULT_RATE = 145
TAIL_SILENCE = 0.8

# Each beat pairs one narration block with the frame it is spoken over.
BEATS = [
    ("frame1.png", "Start small. Scale without re-architecting. "
                   "This is Caldova. It's a biomedical evidence explorer, and underneath it there's just "
                   "one SQL query. Five hundred twelve dimension embeddings, compared with cosine "
                   "distance. That query doesn't change when the database does."),
    ("frame2.png", "Let's ask it something real. How does disruption of the intestinal microbiome "
                   "influence anxiety and depressive symptoms? Nothing in that sentence is a keyword "
                   "match. The embeddings do the work, and every answer comes back tied to the article "
                   "it came from."),
    ("frame3.png", "Each result brings the passages either side of it, so the quote actually reads in "
                   "context instead of stopping mid-sentence."),
    ("frame4.png", "You can also change how it searches. Vector on its own, keyword on its own, or "
                   "hybrid, which fuses both and re-ranks them together. Keyword still wins on rare "
                   "terms, so we run them side by side. And that timing is the vector search itself, "
                   "measured inside the engine, not the round trip."),
    ("portal1.png", "Here's the part I like. This is Hyperscale serverless. It scales down to half a "
                    "vCore, and after an hour of nobody asking it anything, it pauses and you stop paying "
                    "for compute. The next query wakes it back up."),
    ("portal2.png", "And this is what the usage actually looks like. Short bursts, long quiet gaps. Those "
                    "flat stretches are the whole point. I have a job hitting it every three hours, so we "
                    "can watch it pause and resume for real."),
    ("frame5.png", "Now watch what happens when I point the same app at the big database. Same query, "
                   "same vectors, same schema. Only the connection changes. Right now it isn't ready, and "
                   "the timings are blank on purpose. Caldova won't show you a number it can't back up."),
    ("portal3.png", "That database is a different animal. A hundred and ninety-two vCores and almost five "
                    "terabytes, next to the pilot's two."),
    ("portal4.png", "Its corpus is past four hundred million passages across five and a half million "
                    "articles, and it grows while you watch. The team is still loading embeddings on the "
                    "way to a billion rows. That's why there's no vector index on it yet."),
    ("frame6.png", "So here's how we get there without touching their workload. A serverless named "
                   "replica, sharing the same storage, reading the same rows. Its own compute, so the "
                   "loading job never feels us. It's created and wired in. It's waiting on access, which "
                   "is exactly what it says."),
    ("frame7.png", "Start small. Keep the contract steady while the data grows. You shouldn't have to "
                   "rebuild your app just because your corpus did. Start small. Scale without "
                   "re-architecting."),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True)


def duration(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        text=True,
    )
    return float(out.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", type=int, default=DEFAULT_RATE)
    args = parser.parse_args()

    for directory in (AUDIO, BUILD):
        directory.mkdir(parents=True, exist_ok=True)

    segments = []
    for index, (frame, text) in enumerate(BEATS, start=1):
        frame_path = FRAMES / frame
        if not frame_path.exists():
            raise FileNotFoundError(frame_path)

        speech = AUDIO / f"beat{index}.aiff"
        narration = AUDIO / f"beat{index}.wav"
        run(["say", "-v", args.voice, "-r", str(args.rate), str(text), "-o", str(speech)])
        # Pad each beat so the narration does not butt against the next cut.
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(speech),
             "-af", f"aresample=48000,apad=pad_dur={TAIL_SILENCE}",
             "-ac", "2", str(narration)])

        seconds = duration(narration)
        clip = BUILD / f"beat{index}.mp4"
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-loop", "1", "-framerate", "30", "-i", str(frame_path),
             "-i", str(narration),
             "-c:v", "libx264", "-t", f"{seconds:.3f}", "-pix_fmt", "yuv420p",
             "-vf", "scale=1920:1200:force_original_aspect_ratio=decrease,"
                    "pad=1920:1200:(ow-iw)/2:(oh-ih)/2,setsar=1",
             "-c:a", "aac", "-b:a", "192k", "-shortest", str(clip)])
        segments.append((clip, seconds))
        print(f"beat {index:2d}  {frame:<12} {seconds:5.1f}s")

    listing = BUILD / "concat.txt"
    listing.write_text("".join(f"file '{clip.resolve()}'\n" for clip, _ in segments), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(OUTPUT)])

    total = duration(OUTPUT)
    print(json.dumps({
        "output": str(OUTPUT),
        "voice": args.voice,
        "rate": args.rate,
        "beats": len(segments),
        "durationSeconds": round(total, 1),
        "duration": f"{int(total // 60)}:{int(total % 60):02d}",
    }, indent=2))


if __name__ == "__main__":
    main()
