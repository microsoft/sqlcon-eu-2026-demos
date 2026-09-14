#!/usr/bin/env python3
"""Build the Caldova demo recording from narration segments and captured frames."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
FRAMES = ROOT / "frames"
AUDIO = ROOT / "audio"
BUILD = ROOT / "build"
OUTPUT = ROOT / "caldova-demo2.mp4"

# The keynote workspace keeps its own copy so the cut can be reviewed there.
MIRROR = Path(os.environ.get("CALDOVA_MIRROR", str(
    Path.home() / "Library/CloudStorage/OneDrive-Microsoft/Documents/repos"
    / "annahoffmanteam/events/sqlcon-barcelona-2026/keynotedemo2/recording"
    / "caldova-demo2.mp4")))

DEFAULT_VOICE = "Samantha"
DEFAULT_RATE = 145
TAIL_SILENCE = 0.8

WIP_MANIFEST = FRAMES / "wip.json"
WIP_TEXT = "WORK IN PROGRESS  \u00b7  THIS SCREEN IS NOT LIVE YET"

# Each beat pairs one narration block with the frame it is spoken over.
BEATS = [
    ("frame1.png", "Let's look at how you can start small and scale without re-architecting with "
                   "Azure SQL Hyperscale. This is Caldova, a biomedical evidence explorer, and it "
                   "runs on Hyperscale. Every article is chunked into passages, every passage is "
                   "embedded, and a vector index sits over all of them. Underneath the whole app "
                   "there is one SQL query, and that query doesn't change when the database does."),
    ("frame2.png", "Let's ask it something real. How does disruption of the intestinal microbiome "
                   "influence anxiety and depressive symptoms? Nothing in that sentence is a keyword "
                   "match. The meaning is what gets searched, and every answer comes back tied to the "
                   "article it came from."),
    ("frame3.png", "Each result brings the passages either side of it, so the quote actually reads in "
                   "context instead of stopping mid-sentence."),
    ("frame4.png", "So how did that run? This was hybrid. Vector search finds meaning. Keyword "
                   "search finds the exact string, which is what you want for a gene name or a drug "
                   "code. SQL fuses the two rankings together. And the filters run inside the vector "
                   "search rather than after it, so narrowing the evidence doesn't quietly throw away "
                   "the best matches. That timing is the vector search itself, measured inside the "
                   "engine."),
    ("portal1.png", "Here's the part I like. We're just getting started, so this is Hyperscale "
                    "serverless, which now auto-pauses. It scales down to half a vCore, and when "
                    "nobody is searching, it pauses. If the app isn't being used, I'm not getting "
                    "billed for compute."),
    ("portal2.png", "And this is what real usage looks like. Short bursts, long quiet gaps. Those flat "
                    "stretches are the whole point, because the quiet time costs me nothing."),
    ("frame5.png", "Now fast forward. The business grows. Same app, same query, same schema, same "
                   "vector index. I point it at the production corpus and run the same search."),
    ("portal3.png", "This one is a different animal. A hundred and ninety-two vCores and nearly seven "
                    "terabytes of data, next to the pilot's two vCores."),
    ("portal4.png", "Six hundred and sixty-nine million passages across nine million articles, and "
                    "it's still growing, on its way to a billion rows. The vector index never had to "
                    "be rebuilt to get here. Same index, same query, far more rows behind it, and the "
                    "search is just as fast."),
    ("frame6.png", "And because search is read only, I can keep it completely separate with a "
                    "Hyperscale named replica. This is read scale-out on the fly. It uses the same page "
                    "servers as the primary, so there's no data copy, and it comes up in about a "
                    "minute. It gets its own compute, sized independently, so the ingestion workload on "
                    "the primary never feels my queries. You can run up to thirty of them."),
    ("frame7.png", "Start small. Grow big. Keep the contract steady while the data grows. You "
                   "shouldn't have to rebuild your app just because your corpus did. That's "
                   "Hyperscale."),
]


def run(args: list[str]) -> None:
    subprocess.run(args, check=True, capture_output=True)


def wip_frames() -> set[str]:
    if not WIP_MANIFEST.exists():
        return set()
    return set(json.loads(WIP_MANIFEST.read_text(encoding="utf-8")))


def stamp_wip(source: Path, target: Path) -> Path:
    """Overlay an amber work-in-progress banner on a frame that is not live yet."""
    image = Image.open(source).convert("RGB")
    width, height = image.size
    band_height = max(48, height // 18)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(0, 0), (width, band_height)], fill="#f2b705")
    draw.line([(0, band_height), (width, band_height)], fill="#8a6d00", width=3)

    size = max(18, band_height // 2)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
    except OSError:
        font = ImageFont.load_default()

    box = draw.textbbox((0, 0), WIP_TEXT, font=font)
    draw.text(((width - (box[2] - box[0])) / 2, (band_height - (box[3] - box[1])) / 2 - box[1]),
              WIP_TEXT, fill="#1a1400", font=font)
    image.save(target)
    return target


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
    flagged = wip_frames()
    for index, (frame, text) in enumerate(BEATS, start=1):
        frame_path = FRAMES / frame
        if not frame_path.exists():
            raise FileNotFoundError(frame_path)
        if frame in flagged:
            frame_path = stamp_wip(frame_path, BUILD / f"wip-{frame}")

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
        print(f"beat {index:2d}  {frame:<12} {seconds:5.1f}s{'  [WIP banner]' if frame in flagged else ''}")

    listing = BUILD / "concat.txt"
    listing.write_text("".join(f"file '{clip.resolve()}'\n" for clip, _ in segments), encoding="utf-8")
    run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(listing), "-c", "copy", str(OUTPUT)])

    total = duration(OUTPUT)
    mirrored = None
    if MIRROR.parent.is_dir():
        shutil.copy2(OUTPUT, MIRROR)
        mirrored = str(MIRROR)
    print(json.dumps({
        "output": str(OUTPUT),
        "mirroredTo": mirrored,
        "voice": args.voice,
        "rate": args.rate,
        "beats": len(segments),
        "workInProgressFrames": sorted(flagged),
        "durationSeconds": round(total, 1),
        "duration": f"{int(total // 60)}:{int(total % 60):02d}",
    }, indent=2))


if __name__ == "__main__":
    main()
