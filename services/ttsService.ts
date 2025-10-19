import { GoogleGenAI, Modality } from '@google/genai';
import { TtsProvider, VoiceOption } from '../types';
import { base64ToArrayBuffer } from '../utils/audioUtils';

/**
 * A map of API keys for different TTS providers.
 */
type ApiKeyMap = {
  [key in TtsProvider]?: string;
};

/**
 * Fetches the available voices from the ElevenLabs API.
 * @param apiKey The user's ElevenLabs API key.
 * @returns A promise that resolves to an array of VoiceOption objects.
 */
export const getElevenLabsVoices = async (apiKey: string): Promise<VoiceOption[]> => {
  if (!apiKey) return [];

  const url = 'https://api.elevenlabs.io/v1/voices';
  try {
    const response = await fetch(url, {
      headers: {
        'xi-api-key': apiKey,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      throw new Error(`Failed to fetch ElevenLabs voices. Status: ${response.status}. ${errorData?.detail?.message || ''}`);
    }

    const data = await response.json();
    if (!data.voices || !Array.isArray(data.voices)) {
      throw new Error('Invalid response structure from ElevenLabs voices API.');
    }

    // Map the response to our VoiceOption type, creating a descriptive name
    return data.voices.map((voice: any) => {
      const description = [voice.labels?.description, voice.labels?.accent]
        .filter(Boolean)
        .map(s => (s as string).charAt(0).toUpperCase() + (s as string).slice(1))
        .join(', ');
      
      return {
        id: voice.voice_id,
        name: `${voice.name}${description ? ` (${description})` : ''}`,
      };
    });
  } catch (error) {
    console.error('Error fetching ElevenLabs voices:', error);
    if (error instanceof Error) throw error;
    throw new Error('An unexpected error occurred while fetching ElevenLabs voices.');
  }
};


/**
 * Generates speech from text using the selected TTS provider.
 * @param text - The text to convert to speech.
 * @param provider - The TTS provider to use.
 * @param voiceId - The specific voice to use for generation.
 * @param apiKeys - A map containing API keys for third-party services.
 * @returns A promise that resolves to an ArrayBuffer of the audio data.
 */
export const generateSpeech = async (
  text: string,
  provider: TtsProvider,
  voiceId: string,
  apiKeys: ApiKeyMap,
): Promise<ArrayBuffer> => {
  switch (provider) {
    case TtsProvider.Google:
      return generateGoogleTts(text, voiceId);
    case TtsProvider.ElevenLabs:
      return generateElevenLabsTts(text, voiceId, apiKeys[TtsProvider.ElevenLabs]);
    case TtsProvider.HumeAI:
      return generateHumeTts(text, voiceId, apiKeys[TtsProvider.HumeAI]);
    default:
      throw new Error('Unsupported TTS provider.');
  }
};

const generateGoogleTts = async (text: string, voiceId: string): Promise<ArrayBuffer> => {
  if (!process.env.API_KEY) {
    throw new Error('Gemini API key is not configured.');
  }
  
  try {
    const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });
    
    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash-preview-tts",
      contents: [{ parts: [{ text }] }],
      config: {
        responseModalities: [Modality.AUDIO],
        speechConfig: {
          voiceConfig: {
            prebuiltVoiceConfig: { voiceName: voiceId },
          },
        },
      },
    });

    const part = response.candidates?.[0]?.content?.parts?.[0];
    const base64Audio = part && 'inlineData' in part ? part.inlineData?.data : undefined;


    if (!base64Audio) {
      console.error('Unexpected Gemini API response structure:', JSON.stringify(response, null, 2));
      throw new Error('No audio data received from Gemini API. The response may have been blocked or contained an error.');
    }

    return base64ToArrayBuffer(base64Audio);
  } catch (error) {
    console.error('Error generating Google TTS:', error);
    if (error instanceof Error) {
        if (error.message.startsWith('Gemini API Error:') || error.message.startsWith('No audio data')) {
            throw error;
        }
        throw new Error(`Gemini API Error: ${error.message}`);
    }
    throw new Error('An unexpected error occurred during audio generation.');
  }
};

const generateElevenLabsTts = async (text: string, voiceId: string, apiKey?: string): Promise<ArrayBuffer> => {
  if (!apiKey) {
    throw new Error('ElevenLabs API key is required. Please add it in the settings.');
  }

  const ELEVENLABS_API_URL = `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`;
  
  try {
    const response = await fetch(ELEVENLABS_API_URL, {
      method: 'POST',
      headers: {
        'Accept': 'audio/mpeg',
        'Content-Type': 'application/json',
        'xi-api-key': apiKey,
      },
      body: JSON.stringify({
        text: text,
        model_id: "eleven_multilingual_v2",
        voice_settings: {
          stability: 0.5,
          similarity_boost: 0.75,
        },
      }),
    });

    if (!response.ok) {
       const errorData = await response.json().catch(() => ({ detail: { message: 'Unknown error occurred' } }));
       throw new Error(`ElevenLabs API Error: ${errorData.detail?.message || response.statusText}`);
    }

    const audioBlob = await response.blob();
    return await audioBlob.arrayBuffer();
    
  } catch (error) {
    console.error('Error with ElevenLabs API:', error);
     if (error instanceof Error) {
        throw error;
    }
    throw new Error('Failed to generate audio from ElevenLabs.');
  }
};

/**
 * Illustrative function for generating speech with Hume AI.
 * NOTE: This is a placeholder and does not make a real API call.
 */
const generateHumeTts = async (text: string, voiceId: string, apiKey?: string): Promise<ArrayBuffer> => {
  if (!apiKey) {
    throw new Error('Hume AI API key is required. Please add it in the settings.');
  }

  // For this example, we throw an error to indicate it's not implemented.
  throw new Error('Hume AI TTS is for demonstration purposes. The API call structure is available in `services/ttsService.ts`.');
};