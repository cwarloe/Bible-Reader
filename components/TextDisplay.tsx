import React from 'react';
import { Verse, ThemedVerseGroup } from '../types';
import Spinner from './Spinner';
import { formatTime } from '../utils/audioUtils';

interface TextDisplayProps {
  verseGroups: ThemedVerseGroup[];
  isLoading: boolean;
  onGenerateAudio: (verse: Verse) => void;
  generatingAudioForVerse: Verse | null;
  onPlayPause: (verseRef: string) => void;
  playingVerseRef: string | null;
  playbackProgress: number;
  onSeek: (verseRef: string, newProgress: number) => void;
}

const GenerateIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
        <path d="M10 3.5a.75.75 0 01.75.75v4.5a.75.75 0 01-1.5 0V4.25A.75.75 0 0110 3.5z" />
        <path fillRule="evenodd" d="M3.185 8.91a.75.75 0 011.06 0l2.5 2.5a.75.75 0 11-1.06 1.06l-2.5-2.5a.75.75 0 010-1.06zM16.815 8.91a.75.75 0 010 1.06l-2.5 2.5a.75.75 0 11-1.06-1.06l2.5-2.5a.75.75 0 011.06 0z" clipRule="evenodd" />
        <path d="M10 2a.75.75 0 01.75.75v.251a7.5 7.5 0 016.342 6.342.75.75 0 01-1.498.016 6 6 0 00-11.688 0 .75.75 0 11-1.498-.016A7.5 7.5 0 019.25 2.251V2A.75.75 0 0110 2z" />
    </svg>
);

const PlayIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
    </svg>
);

const PauseIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h1a1 1 0 100-2H9V8a1 1 0 00-1-1zm4 0a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
    </svg>
);


const TextDisplay: React.FC<TextDisplayProps> = ({ 
  verseGroups, 
  isLoading, 
  onGenerateAudio,
  generatingAudioForVerse,
  onPlayPause,
  playingVerseRef,
  playbackProgress,
  onSeek,
}) => {
  if (isLoading) {
    return (
      <div className="w-full h-48 bg-brand-bg rounded-lg flex items-center justify-center">
        <p className="text-brand-text-muted animate-pulse">Loading verse...</p>
      </div>
    );
  }

  if (verseGroups.length === 0) {
    return (
      <div className="w-full h-48 bg-brand-bg rounded-lg flex items-center justify-center">
        <p className="text-brand-text-muted">Verse text will appear here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {verseGroups.map((group, groupIndex) => (
        <div key={groupIndex} className="space-y-4">
          <h2 className="text-2xl font-bold text-brand-primary font-serif border-b-2 border-brand-primary/30 pb-2">
            {group.theme}
          </h2>
          {group.verses.map((verse, verseIndex) => {
            const isGenerating = generatingAudioForVerse?.reference === verse.reference;
            const isPlaying = playingVerseRef === verse.reference;
            const progress = isPlaying ? playbackProgress : 0;
            return (
              <div key={verseIndex} className="bg-brand-bg p-4 sm:p-5 rounded-lg shadow-md transition-all duration-300 ease-in-out">
                <h3 className="font-bold text-md text-brand-secondary font-sans mb-2">{verse.reference}</h3>
                <p className="font-serif text-lg leading-relaxed text-brand-text whitespace-pre-wrap">
                  {verse.text}
                </p>

                {verse.audio && (
                  <div className="mt-4 flex items-center gap-3">
                    <button 
                      onClick={() => onPlayPause(verse.reference)}
                      className="text-brand-primary flex-shrink-0 hover:text-brand-secondary transition-colors"
                      aria-label={isPlaying ? `Pause audio for ${verse.reference}` : `Play audio for ${verse.reference}`}
                    >
                      {isPlaying ? <PauseIcon /> : <PlayIcon />}
                    </button>
                    <div className="flex-grow flex items-center gap-2 text-xs text-brand-text-muted">
                      <span className="font-mono w-10 text-center">{formatTime(isPlaying ? verse.audio.duration * (progress / 100) : 0)}</span>
                      <div 
                        className="w-full bg-brand-surface h-1.5 rounded-full cursor-pointer group relative"
                        onClick={(e) => {
                          const rect = e.currentTarget.getBoundingClientRect();
                          const x = e.clientX - rect.left;
                          onSeek(verse.reference, x / rect.width);
                        }}
                      >
                        <div className="bg-brand-text-muted h-1.5 rounded-full" style={{ width: `${progress}%` }}></div>
                        <div 
                          className="absolute top-1/2 h-3 w-3 bg-brand-primary rounded-full shadow-lg transition-opacity"
                          style={{ left: `${progress}%`, transform: 'translate(-50%, -50%)', opacity: isPlaying ? 1 : 0 }}
                        ></div>
                      </div>
                      <span className="font-mono w-10 text-center">{formatTime(verse.audio.duration)}</span>
                    </div>
                  </div>
                )}

                <div className="mt-3 flex items-center justify-between gap-4">
                  <div className="text-xs text-brand-text-muted">
                    {verse.audio && (
                      <p>Audio: <span className="font-semibold">{verse.audio.provider} - {verse.audio.voiceName}</span></p>
                    )}
                  </div>
                  <button 
                    onClick={() => onGenerateAudio(verse)} 
                    disabled={isGenerating}
                    className={`ml-auto flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md transition-all duration-200 ease-in-out bg-white/10 text-brand-text-muted ${isGenerating ? 'opacity-75 cursor-wait animate-pulse' : 'hover:bg-white/20'}`}
                    aria-label={`Generate audio for ${verse.reference}`}
                  >
                    {isGenerating ? <Spinner /> : <GenerateIcon />}
                    {isGenerating ? 'Generating...' : (verse.audio ? 'Regenerate' : 'Generate Audio')}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      ))}
    </div>
  );
};

export default TextDisplay;
