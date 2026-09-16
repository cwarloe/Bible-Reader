#!/usr/bin/env python3
"""
Batch builder for the self-talk library.

Reads content/_manifest.yaml and generates + assembles every enabled track
in order, one at a time. Safe to run overnight — it skips tracks that
already have an output file (unless --force is given), and continues past
failures by default.

Usage:
    # Dry run — show what would be done, touch nothing:
    python build_all.py --dry-run

    # Build everything:
    python build_all.py --yes

    # Build a single category:
    python build_all.py --category identity --yes

    # Build a single track type across all categories:
    python build_all.py --track morning --yes

    # Rebuild already-built tracks (e.g. voice change):
    python build_all.py --force --yes
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

import yaml

CONTENT_DIR = Path(__file__).parent / "content"
MANIFEST_PATH = CONTENT_DIR / "_manifest.yaml"
CONFIG_PATH = Path(__file__).parent / "config.yaml"


def load_manifest() -> list[dict]:
    """Return a flat list of track entries with 'category' and 'file' keys."""
    with open(MANIFEST_PATH) as f:
        manifest = yaml.safe_load(f)

    tracks = []
    for cat in manifest.get("categories", []):
        for track in cat.get("tracks", []):
            if not track.get("enabled", True):
                continue
            tracks.append({
                "category": cat["slug"],
                "category_label": cat["label"],
                "slug": track["slug"],
                "file": CONTENT_DIR / track["file"],
            })
    return tracks


def output_exists(slug: str, config_path: Path) -> bool:
    """Return True if this track already has a built output file."""
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    out_dir = Path(cfg.get("output_dir", "output"))
    if not out_dir.is_absolute():
        out_dir = config_path.parent / out_dir
    # Check for any file whose name starts with the slug
    return any(out_dir.glob(f"{slug}.*"))


def run_step(cmd: list[str], label: str) -> bool:
    """Run a subprocess step. Returns True on success."""
    print(f"  → {label}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"  ✗ FAILED (exit {result.returncode})")
        return False
    print(f"  ✓ done")
    return True


def build_track(slug: str, file: Path, args: argparse.Namespace) -> str:
    """Generate and build one track. Returns 'ok', 'skip', or 'fail'."""
    config = str(CONFIG_PATH) if CONFIG_PATH.exists() else "config.yaml"

    if not args.force and output_exists(slug, Path(config)):
        print(f"\n[{slug}] Already built — skipping (use --force to rebuild)")
        return "skip"

    print(f"\n[{slug}]")

    if args.dry_run:
        print(f"  → selftalk generate --only {slug} --yes")
        print(f"  → selftalk build --only {slug}")
        return "skip"

    # Generate takes
    ok = run_step(
        ["selftalk", "generate", "--config", config, "--content", str(CONTENT_DIR),
         "--only", slug, "--yes"],
        f"generate {slug}",
    )
    if not ok:
        return "fail"

    # Small pause between generate and build (avoids hammering the API)
    time.sleep(1)

    # Assemble
    ok = run_step(
        ["selftalk", "build", "--config", config, "--content", str(CONTENT_DIR),
         "--only", slug],
        f"build {slug}",
    )
    if not ok:
        return "fail"

    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would run, touch nothing")
    parser.add_argument("--yes", action="store_true",
                        help="skip per-track cost confirmations (required unless --dry-run)")
    parser.add_argument("--force", action="store_true",
                        help="rebuild tracks that already have output files")
    parser.add_argument("--category", metavar="SLUG",
                        help="only process this category (e.g. identity)")
    parser.add_argument("--track", choices=["morning", "daytime", "evening"],
                        help="only process this track type")
    parser.add_argument("--stop-on-failure", action="store_true",
                        help="halt immediately on first failure (default: continue)")
    args = parser.parse_args()

    if not args.dry_run and not args.yes:
        print("Pass --yes to confirm, or --dry-run to preview. Aborting.")
        return 1

    tracks = load_manifest()

    # Apply filters
    if args.category:
        tracks = [t for t in tracks if t["category"] == args.category]
        if not tracks:
            print(f"No tracks found for category '{args.category}'.")
            return 1

    if args.track:
        tracks = [t for t in tracks if args.track in t["slug"]]
        if not tracks:
            print(f"No tracks found for track type '{args.track}'.")
            return 1

    print(f"Self-Talk Batch Builder")
    print(f"{'DRY RUN — ' if args.dry_run else ''}{len(tracks)} track(s) to process")
    if args.category:
        print(f"Category filter: {args.category}")
    if args.track:
        print(f"Track filter: {args.track}")

    results: dict[str, str] = {}
    for t in tracks:
        result = build_track(t["slug"], t["file"], args)
        results[t["slug"]] = result
        if result == "fail" and args.stop_on_failure:
            print("\nStopped on failure (--stop-on-failure).")
            break

    # Summary
    ok = sum(1 for r in results.values() if r == "ok")
    skipped = sum(1 for r in results.values() if r == "skip")
    failed = sum(1 for r in results.values() if r == "fail")

    print(f"\n{'=' * 50}")
    print(f"Done: {ok} built, {skipped} skipped, {failed} failed")

    if failed:
        print("\nFailed tracks:")
        for slug, r in results.items():
            if r == "fail":
                print(f"  {slug}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
