import { TtsProvider, VoiceOption } from '../types';

type VoiceMap = {
  [key in TtsProvider]: VoiceOption[];
};

export const TTS_VOICES: VoiceMap = {
  [TtsProvider.Google]: [
    { id: 'Kore', name: 'Kore (Female)' },
    { id: 'Puck', name: 'Puck (Male)' },
    { id: 'Charon', name: 'Charon (Male)' },
    { id: 'Zephyr', name: 'Zephyr (Female)' },
    { id: 'Fenrir', name: 'Fenrir (Male)' },
  ],
  [TtsProvider.ElevenLabs]: [
    { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel (Calm, American)' },
    { id: '2EiwWnXFnvU5JabPnv8n', name: 'Clyde (Authoritative, American)' },
    { id: '5Q0t7uMcjvnagumLfvZi', name: 'James (Older, British)' },
    { id: 'CYw3kZ02Hs0563khs1Fj', name: 'Gigi (Child-like, American)' },
    { id: 'AZnzlk1XvdvUeBnXmlld', name: 'Freya (Youthful, American)' },
  ],
  [TtsProvider.HumeAI]: [
    { id: 'mock-hume-1', name: 'Empathetic Voice 1 (Mock)' },
    { id: 'mock-hume-2', name: 'Calm Voice (Mock)' },
  ],
};
