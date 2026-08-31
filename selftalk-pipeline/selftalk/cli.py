"""Command line entry point.

    selftalk stats                 what each program costs and how long it runs
    selftalk validate              pre-flight checks, before spending credits
    selftalk voices                list your ElevenLabs voices, to pick a voice_id
    selftalk plan                  what a generate run would call the API for
    selftalk generate [--sample N] render the takes, or just the first N of them
    selftalk build                 stitch takes into finished session tracks
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assemble import AssemblyError, assemble_program, plan_layout
from .config import load_config
from .estimate import estimate_program, format_duration, words_needed_for
from .generate import (
    GenerationError,
    list_voices,
    plan_generation,
    resolve_api_key,
    synthesize,
    write_manifest,
)
from .model import ContentError, Program, discover_programs, load_program
from .validate import has_errors, validate_program


def _select(content_root: Path, only: str | None) -> list[Program]:
    programs = discover_programs(content_root)
    if only:
        programs = [p for p in programs if p.slug == only or (p.path and p.path.stem == only)]
        if not programs:
            raise SystemExit(f"no program matching {only!r} under {content_root}")
    return programs


def cmd_stats(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    programs = _select(args.content, args.only)

    total_chars = 0
    for program in programs:
        pacing = config.pacing_for(program.track_type, program.pacing_overrides)
        estimate = estimate_program(program, pacing)
        chars = sum(b.char_count for b in program.all_blocks())
        total_chars += chars

        target = f" (target {program.target_minutes:g}m)" if program.target_minutes else ""
        print(f"\n{program.slug}  [{program.track_type}/{program.perspective}]{target}")
        print(f"  {program.title}")
        print(
            f"  {len(program.blocks)} blocks | {program.word_count} spoken words | "
            f"{chars} billable chars"
        )
        print(
            f"  estimated {format_duration(estimate.total_ms)} "
            f"= {format_duration(estimate.speech_ms)} speech + {format_duration(estimate.silence_ms)} silence"
        )

        if program.target_minutes:
            needed = words_needed_for(program.target_minutes, pacing, estimate.silence_ms)
            words_by_id = {b.id: b.word_count for b in program.all_blocks()}
            spoken_words = sum(b.repeat * words_by_id[b.block_id] for b in estimate.blocks)
            delta = needed - spoken_words
            if abs(delta) > needed * 0.05:
                verb = "add" if delta > 0 else "cut"
                print(f"  -> {verb} roughly {abs(delta)} spoken words to hit the target")

        if args.verbose:
            for b in estimate.blocks:
                print(f"     {b.block_id:<28} x{b.repeat}  {format_duration(b.total_ms)}")

    print(f"\n{len(programs)} program(s), {total_chars} billable characters if fully regenerated.")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    programs = _select(args.content, args.only)

    all_findings = []
    for program in programs:
        pacing = config.pacing_for(program.track_type, program.pacing_overrides)
        all_findings.extend(validate_program(program, pacing))

    for finding in all_findings:
        print(finding)

    errors = sum(1 for f in all_findings if f.severity == "error")
    warnings = len(all_findings) - errors
    print(f"\n{len(programs)} program(s) checked: {errors} error(s), {warnings} warning(s).")
    return 1 if errors else 0


def cmd_plan(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    programs = _select(args.content, args.only)

    grand_total = 0
    for program in programs:
        voice = config.voice_for(program.voice_overrides)
        plan = plan_generation(program, voice, config.raw_dir)
        grand_total += plan.billable_chars

        print(f"\n{program.slug}")
        print(f"  {len(plan.cached)} take(s) cached, {len(plan.to_generate)} to generate")
        if plan.to_generate:
            print(f"  {plan.billable_chars} characters would be billed:")
            for block, _ in plan.to_generate:
                print(f"    + {block.id} ({block.char_count} chars)")
        if plan.stale:
            print(f"  {len(plan.stale)} stale take(s) no longer referenced (safe to delete)")

    print(f"\nTotal to bill: {grand_total} characters.")
    return 0


def cmd_voices(args: argparse.Namespace) -> int:
    """List the account's voices so a voice_id can be copied into config.yaml."""
    try:
        voices = list_voices(resolve_api_key(args.api_key))
    except GenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not voices:
        print("No voices on this account.")
        return 0

    current = load_config(args.config).voice.voice_id
    width = max(len(v["name"]) for v in voices)

    for voice in voices:
        marker = " <- current" if voice["voice_id"] == current else ""
        print(f'{voice["voice_id"]}  {voice["name"]:<{width}}  {voice["labels"]}{marker}')

    print(f"\n{len(voices)} voice(s). Copy an id into elevenlabs.voice_id in config.yaml.")
    return 0

def cmd_generate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    programs = _select(args.content, args.only)

    # Never spend credits on content that would not survive validation.
    for program in programs:
        pacing = config.pacing_for(program.track_type, program.pacing_overrides)
        findings = validate_program(program, pacing)
        if has_errors(findings):
            for finding in findings:
                print(finding, file=sys.stderr)
            print(f"\n{program.slug} has validation errors; fix them first.", file=sys.stderr)
            return 1

    plans = []
    total_chars = 0
    for program in programs:
        voice = config.voice_for(program.voice_overrides)
        plan = plan_generation(program, voice, config.raw_dir).sample(args.sample)
        plans.append((program, voice, plan))
        total_chars += plan.billable_chars

    if total_chars == 0:
        print("Everything is already cached; nothing to generate.")
        return 0

    scope = f" (sample of the first {args.sample} per program)" if args.sample else ""
    print(f"About to generate {sum(len(p.to_generate) for _, _, p in plans)} take(s), "
          f"{total_chars} billable characters{scope}.")
    if not args.yes:
        answer = input("Proceed? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 0

    try:
        api_key = resolve_api_key(args.api_key)
    except GenerationError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for program, voice, plan in plans:
        for block, path in plan.to_generate:
            path.parent.mkdir(parents=True, exist_ok=True)
            print(f"  generating {program.slug}/{block.id} ({block.char_count} chars)")
            try:
                path.write_bytes(synthesize(block.text, voice, api_key))
            except GenerationError as exc:
                print(f"    failed: {exc}", file=sys.stderr)
                return 1
        write_manifest(config.raw_dir, program, voice)

    if args.sample:
        print(
            "\nSample done. Hear it with:\n"
            "  selftalk build --allow-missing"
            + (f" --only {args.only}" if args.only else "")
            + "\nThen re-run generate without --sample for the full track."
        )
    else:
        print("Done.")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    programs = _select(args.content, args.only)

    for program in programs:
        pacing = config.pacing_for(program.track_type, program.pacing_overrides)
        voice = config.voice_for(program.voice_overrides)

        if args.dry_run:
            print(f"\n{program.slug} timeline:")
            for block_id, repeat, gap, trailing in plan_layout(program, pacing):
                print(f"  {block_id:<28} x{repeat}  gap {gap}ms  then {trailing}ms")
            continue

        try:
            report = assemble_program(program, config, voice, pacing, strict=not args.allow_missing)
        except AssemblyError as exc:
            print(f"{program.slug}: {exc}", file=sys.stderr)
            return 1

        print(f"{program.slug}: {report.output_path} ({format_duration(report.duration_ms)})")
        if report.missing:
            print(f"  warning: skipped {len(report.missing)} missing take(s)")

    return 0


def build_parser() -> argparse.ArgumentParser:
    # Shared options live on a parent parser so they work in the position users
    # actually type them: `selftalk build --only foo`, not `selftalk --only foo build`.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default="config.yaml", type=Path)
    common.add_argument("--content", default="content", type=Path)
    common.add_argument("--only", help="operate on a single program slug")

    parser = argparse.ArgumentParser(prog="selftalk", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    p_stats = sub.add_parser("stats", parents=[common], help="word counts, character cost, estimated runtime")
    p_stats.add_argument("-v", "--verbose", action="store_true", help="per-block breakdown")
    p_stats.set_defaults(func=cmd_stats)

    sub.add_parser("validate", parents=[common], help="pre-flight checks").set_defaults(func=cmd_validate)
    sub.add_parser("plan", parents=[common], help="show what generation would cost").set_defaults(func=cmd_plan)

    p_voices = sub.add_parser("voices", parents=[common], help="list your ElevenLabs voices")
    p_voices.add_argument("--api-key", help="overrides ELEVENLABS_API_KEY")
    p_voices.set_defaults(func=cmd_voices)

    p_gen = sub.add_parser("generate", parents=[common], help="render missing takes via ElevenLabs")
    p_gen.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    p_gen.add_argument("--api-key", help="overrides ELEVENLABS_API_KEY")
    p_gen.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="generate only the first N takes per program — prove the voice and "
             "pacing cheaply before committing to the whole track",
    )
    p_gen.set_defaults(func=cmd_generate)

    p_build = sub.add_parser("build", parents=[common], help="assemble takes into finished tracks")
    p_build.add_argument("--dry-run", action="store_true", help="print the timeline, touch no audio")
    p_build.add_argument("--allow-missing", action="store_true", help="skip ungenerated takes")
    p_build.set_defaults(func=cmd_build)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except ContentError as exc:
        print(f"content error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
