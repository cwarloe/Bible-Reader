# Roadmap

The point of this file is to make "am I done?" answerable without thinking about
it. Each milestone has a definition of done that is checkable, not a vibe.

**Status legend:** `[x]` done · `[ ]` not started · `[~]` in progress

---

## Where this stands today

Milestone 0 is complete and Milestone 1 is roughly half done. The pipeline runs
end to end in dry-run: content validates, cost is knowable before you spend, and
the assembler produces a timeline. What has never happened yet is a real
ElevenLabs call — that is the M1 gate.

---

## M0 — Foundation ✅

*Done means: the scripts are out of Google Docs and under version control, and
the tooling can read them.*

- [x] Content schema — one YAML file per track, blocks as the unit of work
- [x] Ephesians 4–6 morning scripts migrated out of Google Docs (3 tracks)
- [x] Ephesians 4 daytime drill migrated, with its synthesis coda (1 track)
- [x] `selftalk stats` — word count, character cost, estimated runtime
- [x] `selftalk validate` — pre-flight checks
- [x] Test suite covering the schema, estimator, validator, cache, and assembler

---

## M1 — MVP 🎯

**One track you actually listen to, produced entirely by this repo.**

That is the whole bar. Not the full library, not every track type — one finished
mp3 that came out of `selftalk build`, that you put on in the morning.

*Done means: `selftalk generate --only eph-01-morning-identity-walk && selftalk
build --only eph-01-morning-identity-walk` produces an 8-minute mp3 you have
listened to start to finish.*

- [x] Content-hash cache so an edited line regenerates that line and nothing else
- [x] `selftalk plan` — see the character cost before committing to it
- [x] Assembler with per-track-type pacing (morning / daytime / night)
- [ ] Pick and record the voice ID in `config.yaml`
- [ ] First real generation run against the ElevenLabs API
- [ ] First assembled master track
- [ ] Listen to it end to end and write down what is wrong with it

**The last item is the real deliverable.** Everything before it is scaffolding.
Expect the first listen to change the pacing constants — that is what it is for.

---

## M2 — Functional

**The daily rotation works, and producing a new track is boring.**

*Done means: you have a morning, a daytime, and a night track for one suite, and
adding a fourth is a YAML edit plus two commands.*

- [ ] Pacing constants tuned against the first real listen (M1's finding)
- [ ] Ephesians night track written — the format not yet drafted anywhere
- [ ] Ephesians 5–6 daytime drill (currently only Ephesians 4 exists)
- [ ] Morning tracks brought to their 8-minute target (`stats` says 01 and 03 run short)
- [ ] Daytime drill brought down to target (`stats` says it runs 10m21s)
- [ ] A written answer to "how do I get these onto my phone?"

That last one is not a footnote. A pipeline that ends in `output/master/` and not
in your ears is not functional.

---

## M3 — The library

**Enough content that the rotation does not repeat inside a week.**

The candidate suites, why they exist, and the worldview problem to avoid when
adapting them are worked out in [`docs/CONTENT-STRATEGY.md`](docs/CONTENT-STRATEGY.md).
Read that before writing a new suite — a straight port of the reference material
lands you in "it's all up to you" territory, which does not survive contact with
John 15:5.

Build these three, in this order, and then reassess:

- [ ] **Identity in Christ** (Ephesians 1:3–14) — the indicative every other
      suite assumes; nearly zero adaptation needed
- [ ] **Peace & Anxiety** (Philippians 4:4–9) — highest felt need, and forces
      the night format to be solved once
- [ ] **Psalms of Self-Address** (Ps 42, 62, 103) — the method's own source text

Supporting work:

- [ ] Suite-level manifest — what belongs to a suite, in what order
- [ ] `selftalk build` for a whole suite in one command
- [ ] Playlist or per-suite output folders

**Do not plan past this.** Twelve suites at four tracks each is 48 tracks. At
three finished tracks you will know more about what you actually listen to than
any plan written today.

---

## M4 — Quality of life

Only after M3. Everything here is a convenience, not a capability.

- [ ] Background music or ambience bed under the master track
- [ ] Loudness normalization so tracks match volume
- [ ] Silence trimming on raw takes so pacing constants mean what they say
- [ ] Per-block voice overrides (a different voice for the synthesis coda)
- [ ] CI running `validate` and the test suite on every push
- [ ] Listening log — which track, which day, what you noticed

---

## Explicitly not doing

Worth writing down so it stops coming up.

- **A web UI.** The YAML is the interface. Revisit only if editing gets painful.
- **Rebuilding a TTS engine.** ElevenLabs is the vendor; the pipeline stays thin
  enough to swap it.
- **Redistributing the reference programs.** The Helmstetter transcripts are
  studied for their structure and stay out of the repo — see
  `docs/PATTERNS.md` for the structure itself, which is what is actually useful.

---

## How to stay on track

One rule: **finish M1 before touching anything in M2.**

The failure mode for this project is not lack of ideas, it is breadth. There are
four scripts in `content/` and zero minutes of finished audio. The gap between
those two numbers is the only thing that matters right now, and every item in M2
onward is a way to avoid closing it.

When you are unsure what to do next, run `selftalk stats` and pick the first
unchecked box in the earliest incomplete milestone.
