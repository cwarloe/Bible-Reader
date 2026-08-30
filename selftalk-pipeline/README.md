# selftalk-pipeline

Scripts in YAML, finished listening sessions out. A pipeline for producing
Helmstetter-pattern self-talk audio — morning directives, daytime repetition
drills, night integration tracks — from version-controlled text.

**Start here:** [`ROADMAP.md`](ROADMAP.md) — what's done, what MVP means, what's next.

---

## Why this exists

The scripts were spread across Google Docs and chat logs, the audio was
hand-assembled, and there was no way to answer "will this run eight minutes?"
without generating it first. This repo makes the text the source of truth and
everything else a build step.

Three problems it solves specifically:

**Credits.** A daytime drill says each line three times. Generated as one long
take that is 3× the characters; generated per line and repeated by the
assembler it is 1×. Every take is cached against a hash of its text and voice
settings, so editing one line regenerates that line and nothing else.

**Runtime.** `selftalk stats` estimates duration from word count, speaking rate
and the silence budget — including the repeats. It tells you how many words to
add or cut before you spend anything.

**Mistakes that cost a re-record.** `selftalk validate` rejects SSML (v3 reads
`<break>` tags out loud), blocks over the 5000-character generation limit,
duplicate ids, and scripts that miss their target runtime.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env      # add your ELEVENLABS_API_KEY
```

`pydub` needs `ffmpeg` on your PATH for the `build` step. Everything else
(`stats`, `validate`, `plan`) works without it.

Then set `elevenlabs.voice_id` in `config.yaml` to the voice you want.

---

## Workflow

```bash
selftalk stats                    # how long is it, what will it cost
selftalk validate                 # pre-flight, before spending anything
selftalk plan                     # exactly which takes would be billed
selftalk generate --only SLUG     # render missing takes (asks first)
selftalk build --only SLUG        # stitch into output/master/SLUG.mp3
```

Run it as `python3 -m selftalk.cli` if you have not `pip install -e .`'d it.

Every command takes `--only SLUG` to work on one program. `build --dry-run`
prints the timeline without touching audio.

### What `stats` tells you

```
eph-01-morning-identity-walk  [morning/second_person] (target 8m)
  23 blocks | 751 spoken words | 4404 billable chars
  estimated 7m 37s = 7m 09s speech + 0m 28s silence
  -> add roughly 41 spoken words to hit the target
```

---

## Writing a program

Copy `content/templates/_program-template.yaml` into `content/<suite>/`. Files
starting with `_` are skipped by the loader.

A program is a list of **blocks**. A block is one thing you say. How many times
it gets said and how much silence follows comes from the track type — so the
same block list renders as a morning directive or a daytime drill without
editing the content.

```yaml
slug: eph-04-daytime-identity-walk
title: "Ephesians 4 — Identity & Walk (Daytime Drill)"
track_type: daytime          # morning | daytime | night
perspective: first_person
target_minutes: 8

blocks:
  - id: walk-worthy
    text: "I walk in a manner worthy of the calling to which I have been called."

synthesis:                    # daytime only: spoken once, in second person
  id: synthesis-you
  text: |
    This is how you choose to walk each day.
```

Per-block overrides when a line needs different treatment:

```yaml
  - id: opening-tone
    repeat: 1                 # spoken once even on a daytime track
    pause_after_ms: 3000      # override the track's block gap
```

**Block ids are cache keys.** Renaming one forces a regeneration; editing the
text is what should. Keep them stable.

---

## Layout

```
selftalk/            the pipeline
  config.py          defaults, track-type presets, override layering
  model.py           the content schema
  estimate.py        runtime estimation
  validate.py        pre-flight checks
  generate.py        ElevenLabs + content-hash cache
  assemble.py        take stitching and pacing
  cli.py             commands
content/             the scripts — the actual source of truth
  ephesians/         Ephesians 4-6, three morning tracks and one daytime drill
  templates/         starting point for a new program
docs/PATTERNS.md     the structural analysis behind the scripts
output/              gitignored build artifacts
  raw_takes/         one file per block, named by content hash
  master/            finished session tracks
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The suite covers the schema, the estimator's pacing arithmetic, every validation
rule, cache invalidation, and the assembler's timeline — plus a check that every
program in `content/` still validates.

## A note on the reference material

The structure here is derived from Dr. Shad Helmstetter's self-talk programs.
`docs/PATTERNS.md` documents the *form* — perspective, repetition, pacing,
rhetorical devices — which is what is useful for writing new scripts. The
reference transcripts themselves are commercial recordings and stay out of the
repo; `content/reference/` is gitignored if you keep local copies for study.
