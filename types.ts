export enum TtsProvider {
  Google = 'Google Gemini',
  ElevenLabs = 'ElevenLabs',
  HumeAI = 'Hume AI (mock)',
}

export interface VoiceOption {
  id: string;
  name: string;
}

export interface GeneratedAudio {
  buffer: AudioBuffer;
  provider: TtsProvider;
  voiceName: string;
  duration: number;
}

export interface Verse {
  reference: string;
  text: string;
  audio?: GeneratedAudio;
}

export interface ThemedVerseGroup {
  theme: string;
  verses: Verse[];
}

export interface HistoryItem {
  theme: string;
  reference: string;
  playedAt: number;
}
