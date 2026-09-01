<div align="center">
<img width="1200" height="475" alt="GHBanner" src="https://github.com/user-attachments/assets/0aa67016-6eaf-458a-adb2-6e31a0763ed6" />

# 📖 Audio Bible Reader

**Fetch and hear Scripture — powered by AI-driven Text-to-Speech**

[![CI](https://github.com/cwarloe/Bible-Reader/actions/workflows/ci.yml/badge.svg)](https://github.com/cwarloe/Bible-Reader/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![React](https://img.shields.io/badge/React-19-blue?logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-blue?logo=typescript)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.2-purple?logo=vite)](https://vitejs.dev/)

[View in AI Studio](https://ai.studio/apps/drive/1UWLXGxDfNEDFeJXZ4r-xgreh43TPgkvs) &nbsp;•&nbsp; [Report a Bug](.github/ISSUE_TEMPLATE/bug_report.md) &nbsp;•&nbsp; [Request a Feature](.github/ISSUE_TEMPLATE/feature_request.md)

</div>

---

## ✨ Features

- 🎙️ **Multi-provider TTS** — choose between Google Gemini, ElevenLabs, and Hume AI voices
- 📖 **ESV Bible Integration** — fetches verses from the English Standard Version via the ESV API
- 🔐 **Secure API Key Management** — encrypted local storage for your Gemini API key
- 🕰️ **Reading History** — tracks every verse you've listened to with timestamps
- 🎚️ **Playback Controls** — pause, resume, and replay audio with the built-in TTS controls
- 🌐 **AI Studio Ready** — built and tested for deployment on Google AI Studio

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Framework | React 19 + TypeScript 5.8 |
| Build tool | Vite 6.2 |
| Styling | Tailwind CSS (CDN) |
| AI / TTS | Google Gemini (`@google/genai`) |
| Bible data | ESV API |
| Additional TTS | ElevenLabs · Hume AI |

---

## 🚀 Getting Started

### Prerequisites

- **Node.js** v18 or later
- A **Gemini API key** — [get one free at Google AI Studio](https://aistudio.google.com/app/apikey)
- *(Optional)* An **ElevenLabs API key** for additional voices

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/cwarloe/Bible-Reader.git
cd Bible-Reader

# 2. Install dependencies
npm install

# 3. Configure environment variables
cp .env.local.example .env.local   # then edit with your keys
```

### Environment Variables

Create a `.env.local` file in the project root:

```env
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional — enables ElevenLabs voices
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

### Running Locally

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

```bash
npm run build   # outputs to dist/
npm run preview # preview the production build locally
```

---

## 📁 Project Structure

```
Bible-Reader/
├── App.tsx                 # Root application component
├── index.tsx               # React DOM entry point
├── index.html              # HTML shell (Tailwind CDN + import map)
├── types.ts                # Shared TypeScript interfaces
│
├── components/             # UI components
│   ├── ApiKeyManager.tsx   # API key input & encrypted storage
│   ├── History.tsx         # Reading history panel
│   ├── Spinner.tsx         # Loading indicator
│   ├── TextDisplay.tsx     # Verse text renderer
│   ├── TtsControls.tsx     # Audio playback controls
│   └── VerseSelector.tsx   # Book / chapter / verse picker
│
├── services/               # Business logic & external APIs
│   ├── cryptoService.ts    # AES encryption for stored keys
│   ├── dbService.ts        # IndexedDB persistence
│   ├── esvService.ts       # ESV Bible API client
│   ├── ttsService.ts       # TTS orchestration layer
│   └── ttsVoices.ts        # Voice provider definitions
│
└── utils/
    └── audioUtils.ts       # Audio buffer helpers
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push to your fork: `git push origin feat/my-feature`
5. Open a Pull Request using the provided template

Please report bugs and request features using the issue templates in `.github/ISSUE_TEMPLATE/`.

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](./LICENSE) file for details.
