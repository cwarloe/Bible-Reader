# The pattern reference

The structural analysis behind the scripts, extracted so it does not live in a
chat log. This describes the *form* of the reference programs; the reference
transcripts themselves are commercial recordings and are not in this repo.

---

## The three track types

| | Morning | Daytime | Night |
|---|---|---|---|
| **Role** | The Directive | The Conditioning | The Integration |
| **Person** | second ("you") | first ("I") → second coda | second ("you") |
| **Repetition** | none | every line ×3 | none |
| **Gap between repeats** | — | ~1.1s | — |
| **Gap between blocks** | ~1.2s | ~2.2s | ~2.5s |
| **Pace** | ~105 wpm | ~105 wpm | ~95 wpm |
| **When** | first thing | commute, walking, background | wind-down |

These live in code as `TRACK_PRESETS` in `selftalk/config.py`. Changing a number
there changes every track of that type.

### Why second person

Standard affirmations use "I". These use "you" throughout, taking the position
of an outside voice rather than an internal claim. The stated rationale is that
an external frame meets less internal argument than a first-person claim the
listener may not yet believe.

The daytime track is the exception, and deliberately so: it drills in first
person, then closes with a second-person coda restating the same material. The
shift is the technique, not an inconsistency.

---

## The rhetorical toolkit

Every device below appears in the shipped scripts. When a draft feels thin, it
is usually missing three or four of these.

**Bookending.** Opens with `These are the programs you choose to have... about
yourself... and [topic].` Closes with `Those are the programs you choose to
have about [topic]. You already know the truth: [claim]... and today is a great
day to prove it.` Thought habits framed as software you are choosing to install.

**The agency anchor.** `You choose` — a dozen-plus times per track. Every claim
is an election, not a description.

**Present-tense declaration.** Nothing aspirational. Not "you will become an
achiever" but "you are an achiever." State the destination as the current
address.

**Tricolons.** Three beats, one per line, at every turn:
`You go for it. / You work at it. / And you achieve it.`
Line breaks matter — v3 treats each line as its own thought.

**The mirror check.** One per morning track. `When you look at yourself in the
mirror, you see yourself as being...` — a deliberate identity confrontation.

**The descriptor series.** Eight to eleven adjectives, ellipses between them, no
conjunctions until the last: `interested... open-minded... actively learning...
capable... and making progress every day.`

**Reframe of difficulty.** Obstacles are never obstacles: "stepping stones along
the way," "turn circumstances into positive advantages."

**Independence with contribution.** Self-reliance, plus explicit interest in
others' growth. "You never rely on others to create your successes" sits beside
"you are interested in the development of others."

**The recursive line.** `Each time you hear these words and think about their
meaning...` — the track commenting on the act of listening to it.

---

## ElevenLabs v3 formatting

**v3 does not support SSML.** No `<break time="1.0s" />`. It is either ignored
or read out loud in the middle of a finished take. The validator rejects it as
an error for exactly this reason.

Pacing in v3 comes from three places instead:

1. **Audio tags** — bracketed direction: `[calm, steady, authoritative,
   unhurried, measured delivery]`, `[deliberate emphasis]`, `[confident and
   clear]`. Put one at the top of a block to set its delivery.
2. **`[pause]` / `[beat]`** — a clean break between concepts. The estimator
   budgets `pause_tag_ms` (default 700ms) for each.
3. **Punctuation and line breaks** — ellipses for drawn-out transitions,
   em-dashes for authoritative mid-sentence shifts, hard returns to force each
   line into its own deliberate thought.

**Voice settings** (in `config.yaml`):

- **Stability 0.65–0.75.** Grounded and rhythmic. Lower and the model gets
  emotionally erratic across a long declarative list.
- **Similarity 0.75–0.85.** Keeps articulation crisp through repetition.
- **Style 0.00–0.10.** Low, so the model does not dramatize or rush the
  descriptor series.

**Character limit: 5000 per generation.** The validator errors above it and
warns above 3000, where delivery starts to drift within a single take.

---

## Why blocks instead of one long script

Three reasons, all practical:

1. **Credits.** A daytime track says each line three times. Generated as one
   long take, that is 3× the characters. Generated per block and repeated by the
   assembler, it is 1×.
2. **Consistency.** Three separate generations of the same sentence come back
   subtly different. One generation played three times is identical every time —
   which is the point of a repetition drill.
3. **Editing.** Change one line and only that line regenerates. The cache is
   keyed on the text plus the voice settings, so nothing else is touched.

---

## Suite architecture

The reference library runs four tracks per topic:

```
01_Morning    8 min   second person, continuous
02_Daytime    8 min   first person ×3 + synthesis coda
03_Daytime    8 min   as above, tactical rather than foundational
04_Night      8 min   second person, slow, release and rest
```

Larger topics get progressive multi-session suites (six sessions, moving from
core beliefs → planning → execution → pressure → review → mastery) rather than a
single deeper track.
