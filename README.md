# Bible Reader

Two related projects for scripture-driven audio.

## `/` — Audio Bible Reader

A React app that fetches ESV passages grouped by theme and reads them aloud with
AI voices (Google Gemini TTS or ElevenLabs). Generated audio and passage text are
cached in IndexedDB, so a verse is fetched and voiced once and then replays
offline. API keys are encrypted with AES-GCM in local storage and never leave the
browser.

**Run it:**

```bash
npm install
echo "GEMINI_API_KEY=your-key" > .env.local   # only needed for Gemini TTS
npm run dev
```

Then add your ESV API key (and ElevenLabs key, if using it) in the app's own
settings panel.

**Input format** — a theme line without digits, followed by its references:

```
Introductions - Church Epistles
Romans 1:1-7
1 Corinthians 1:1-3

Introductions - Pastoral Epistles
1 Timothy 1:1-2
```

## `/selftalk-pipeline` — Self-talk audio pipeline

Turns version-controlled YAML scripts into finished listening sessions:
Helmstetter-pattern morning directives, daytime repetition drills, and night
integration tracks, generated through ElevenLabs and assembled with pydub.

Built around three things the manual process could not do: estimate a track's
runtime before generating it, avoid paying to regenerate lines that have not
changed, and catch the mistakes (SSML in a v3 prompt, an over-length block) that
cost a re-record.

See [`selftalk-pipeline/README.md`](selftalk-pipeline/README.md) to run it and
[`selftalk-pipeline/ROADMAP.md`](selftalk-pipeline/ROADMAP.md) for what's next.
