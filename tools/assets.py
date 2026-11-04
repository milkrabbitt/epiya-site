#!/usr/bin/env python3
"""Optimize verified EPIYA product screenshots without cropping their disclosures.

Run with Pillow installed. Inputs default to ../../product-assets relative to
this script; --source-root can point at a fresh, reviewed asset handoff.
Only resized raster pixels are written, with no EXIF or other source metadata.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageOps


SITE_ROOT = Path(__file__).resolve().parents[1]
SPECS = (
    ("meow/cream-appstore.jpg", "meow-cream.webp", 660,
     "Apple App Store 6813336672, version 2.6: cream theme screenshot", "Published store screenshot"),
    ("meow/strawberry-appstore.jpg", "meow-strawberry.webp", 660,
     "Apple App Store 6813336672, version 2.6: strawberry theme screenshot", "Published store screenshot"),
    ("meow/midnight-appstore.jpg", "meow-midnight.webp", 660,
     "Apple App Store 6813336672, version 2.6: midnight theme screenshot", "Published store screenshot"),
    ("relic/chat-build19.png", "relic-chat.webp", 660,
     "milkrabbitt/relic-showcase assets/ui/after-chat.png", "iOS Simulator build19, synthetic fixture; not live business"),
    ("relic/import-review-build20.png", "relic-import.webp", 660,
     "milkrabbitt/relic-showcase assets/ui/import-review-build20.png", "iOS Simulator build20, synthetic fixture; not live business"),
    ("relic/memory-build20.png", "relic-memory.webp", 660,
     "milkrabbitt/relic-showcase assets/ui/memory-build20.png", "iOS Simulator build20, synthetic fixture; not live business"),
    ("futures/market-v6.png", "futures-market.webp", 1480,
     "Futures Alpha workbench 06 docs/v6-screens/market.png", "Actual desktop screenshot, TqSdk market dry-run; no trading account"),
    ("futures/overview-v6.png", "futures-overview.webp", 1480,
     "Futures Alpha workbench 06 docs/v6-screens/overview.png", "Actual desktop screenshot, dry-run overview; not investment performance"),
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(source_root: Path, output_root: Path) -> list[dict]:
    output_root.mkdir(parents=True, exist_ok=True)
    results = []
    for relative, output_name, max_width, source_description, disclosure in SPECS:
        source = source_root / relative
        destination = output_root / output_name
        with Image.open(source) as original:
            picture = ImageOps.exif_transpose(original)
            original_size = list(picture.size)
            if picture.mode not in ("RGB", "RGBA"):
                picture = picture.convert("RGBA" if "transparency" in picture.info else "RGB")
            if picture.width > max_width:
                height = round(picture.height * max_width / picture.width)
                picture = picture.resize((max_width, height), Image.Resampling.LANCZOS)
            # Keep the full image: Relic's in-image synthetic-data banners remain.
            picture.save(destination, "WEBP", quality=92, method=6)
            intended_size = list(picture.size)
        with Image.open(destination) as decoded:
            decoded.load()
            if decoded.format != "WEBP" or list(decoded.size) != intended_size:
                raise RuntimeError(f"Output verification failed: {output_name}")
            if decoded.width > max_width:
                raise RuntimeError(f"Width limit exceeded: {output_name}")
        results.append({
            "output": f"assets/{output_name}",
            "source": source_description,
            "reviewed_input": relative,
            "disclosure": disclosure,
            "operation": "Full-frame proportional resize and WebP encode; no crop or content edits",
            "source_dimensions": original_size,
            "dimensions": intended_size,
            "source_bytes": source.stat().st_size,
            "bytes": destination.stat().st_size,
            "source_sha256": digest(source),
            "sha256": digest(destination),
        })
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=SITE_ROOT.parent / "product-assets")
    parser.add_argument("--output-root", type=Path, default=SITE_ROOT / "assets")
    args = parser.parse_args()
    results = build(args.source_root, args.output_root)
    manifest = {"checked_date": "2026-11-03", "encoding": "WebP quality 92, method 6", "assets": results}
    (SITE_ROOT / "tools" / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for entry in results:
        print(f"{entry['output']}: {entry['dimensions'][0]}x{entry['dimensions'][1]}, {entry['bytes']} bytes")
    source_bytes = sum(x["source_bytes"] for x in results)
    output_bytes = sum(x["bytes"] for x in results)
    print(f"Verified {len(results)} assets: {source_bytes} -> {output_bytes} bytes ({100*(1-output_bytes/source_bytes):.1f}% smaller)")


if __name__ == "__main__":
    main()
