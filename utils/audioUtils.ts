/**
 * Decodes a base64 string into an ArrayBuffer.
 * @param base64 - The base64 encoded string.
 * @returns An ArrayBuffer of the decoded data.
 */
export function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

// --- Helper function for bufferToWave ---

const writeString = (view: DataView, offset: number, string: string) => {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
};

/**
 * Converts an AudioBuffer to a WAV audio format Blob. This is necessary for storing
 * the audio in IndexedDB in a playable format.
 * @param buffer The AudioBuffer to convert.
 * @returns A Blob containing the WAV audio data.
 */
export const bufferToWave = (buffer: AudioBuffer): Blob => {
  const numOfChan = buffer.numberOfChannels;
  const length = buffer.length * numOfChan * 2 + 44;
  const bufferView = new ArrayBuffer(length);
  const view = new DataView(bufferView);
  const channels = [];
  let i;
  let sample;
  let offset = 0;
  let pos = 0;

  // write WAVE header
  writeString(view, pos, 'RIFF'); pos += 4;
  view.setUint32(pos, length - 8, true); pos += 4;
  writeString(view, pos, 'WAVE'); pos += 4;
  writeString(view, pos, 'fmt '); pos += 4;
  view.setUint32(pos, 16, true); pos += 4; // Sub-chunk size
  view.setUint16(pos, 1, true); pos += 2;  // Audio format 1=PCM
  view.setUint16(pos, numOfChan, true); pos += 2;
  view.setUint32(pos, buffer.sampleRate, true); pos += 4;
  view.setUint32(pos, buffer.sampleRate * 2 * numOfChan, true); pos += 4; // byte rate
  view.setUint16(pos, numOfChan * 2, true); pos += 2; // block align
  view.setUint16(pos, 16, true); pos += 2; // bits per sample
  writeString(view, pos, 'data'); pos += 4;
  view.setUint32(pos, length - pos - 4, true); pos += 4;

  // write interleaved data
  for (i = 0; i < buffer.numberOfChannels; i++) {
    channels.push(buffer.getChannelData(i));
  }

  while (pos < length) {
    for (i = 0; i < numOfChan; i++) {
      sample = Math.max(-1, Math.min(1, channels[i][offset]));
      sample = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
      view.setInt16(pos, sample, true);
      pos += 2;
    }
    offset++;
  }

  return new Blob([view], { type: 'audio/wav' });
};

/**
 * Decodes raw PCM audio data into an AudioBuffer for playback.
 * This is required for Gemini TTS audio, which is not in a standard file format.
 * @param data The raw audio data as a Uint8Array.
 * @param ctx The AudioContext instance.
 * @param sampleRate The sample rate of the audio (Gemini TTS is 24000).
 * @param numChannels The number of channels (Gemini TTS is 1).
 * @returns A promise that resolves to an AudioBuffer.
 */
export async function decodePcmAudioData(
  data: Uint8Array,
  ctx: AudioContext,
  sampleRate: number = 24000,
  numChannels: number = 1,
): Promise<AudioBuffer> {
  // The raw data is 16-bit signed PCM.
  const dataInt16 = new Int16Array(data.buffer, data.byteOffset, data.length / 2);
  const frameCount = dataInt16.length / numChannels;
  const buffer = ctx.createBuffer(numChannels, frameCount, sampleRate);

  for (let channel = 0; channel < numChannels; channel++) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < frameCount; i++) {
      channelData[i] = dataInt16[i * numChannels + channel] / 32768.0;
    }
  }
  return buffer;
}

/**
 * Formats a duration in seconds into a "minutes:seconds" string.
 * @param seconds The total seconds to format.
 * @returns A formatted time string (e.g., "1:23").
 */
export const formatTime = (seconds: number): string => {
  if (isNaN(seconds) || seconds < 0) {
    return '0:00';
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};
