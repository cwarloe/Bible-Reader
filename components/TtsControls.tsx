import React from 'react';
import { TtsProvider, VoiceOption } from '../types';

interface TtsControlsProps {
  selectedProvider: TtsProvider;
  setSelectedProvider: (provider: TtsProvider) => void;
  availableVoices: VoiceOption[];
  selectedVoice: string;
  setSelectedVoice: (voiceId: string) => void;
  speechRate: number;
  setSpeechRate: (rate: number) => void;
  speechPitch: number;
  setSpeechPitch: (pitch: number) => void;
}

const TtsControls: React.FC<TtsControlsProps> = ({
  selectedProvider,
  setSelectedProvider,
  availableVoices,
  selectedVoice,
  setSelectedVoice,
  speechRate,
  setSpeechRate,
  speechPitch,
  setSpeechPitch,
}) => {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-semibold text-brand-text mb-4">Audio Generation</h3>
          <h4 className="text-sm font-medium text-brand-text-muted mb-3">Choose a TTS Provider</h4>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {(Object.values(TtsProvider)).map((provider) => (
              <button
                key={provider}
                onClick={() => setSelectedProvider(provider)}
                className={`px-4 py-2 text-sm font-semibold rounded-md transition-all duration-200 ease-in-out
                  ${selectedProvider === provider
                    ? 'bg-brand-primary text-brand-bg ring-2 ring-offset-2 ring-offset-brand-surface ring-brand-primary'
                    : 'bg-brand-bg text-brand-text-muted hover:bg-white/10'
                  }`}
              >
                {provider}
              </button>
            ))}
          </div>
        </div>
        
        <div>
           <label htmlFor="voice-select" className="block text-sm font-medium text-brand-text-muted mb-2">
            Select a Voice
          </label>
          <select
            id="voice-select"
            value={selectedVoice}
            onChange={(e) => setSelectedVoice(e.target.value)}
            className="w-full bg-brand-bg border border-white/20 text-brand-text rounded-md px-3 py-2 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition duration-150 ease-in-out"
          >
            {availableVoices.map((voice) => (
              <option key={voice.id} value={voice.id}>
                {voice.name}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="border-t border-white/10 my-6"></div>

      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-brand-text">Playback Controls</h3>
        <div>
          <label htmlFor="speech-rate" className="block text-sm font-medium text-brand-text-muted mb-2">
            Speed ({speechRate.toFixed(2)}x)
          </label>
          <input
            type="range"
            id="speech-rate"
            min="0.5"
            max="2"
            step="0.1"
            value={speechRate}
            onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
            className="w-full h-2 bg-brand-bg rounded-lg appearance-none cursor-pointer accent-brand-primary"
          />
        </div>
        <div>
          <label htmlFor="speech-pitch" className="block text-sm font-medium text-brand-text-muted mb-2">
            Pitch ({speechPitch >= 0 ? '+' : ''}{(speechPitch / 100).toFixed(1)} semitones)
          </label>
          <input
            type="range"
            id="speech-pitch"
            min="-1200"
            max="1200"
            step="100"
            value={speechPitch}
            onChange={(e) => setSpeechPitch(parseInt(e.target.value))}
            className="w-full h-2 bg-brand-bg rounded-lg appearance-none cursor-pointer accent-brand-primary"
          />
        </div>
      </div>
    </div>
  );
};

export default TtsControls;
