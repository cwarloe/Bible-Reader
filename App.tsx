import React, { useState, useRef, useCallback, useEffect, useMemo } from 'react';
import { TtsProvider, Verse, GeneratedAudio, ThemedVerseGroup, VoiceOption, HistoryItem } from './types';
import { fetchVerse } from './services/esvService';
import { generateSpeech, getElevenLabsVoices } from './services/ttsService';
import { bufferToWave, decodePcmAudioData } from './utils/audioUtils';
import { TTS_VOICES } from './services/ttsVoices';
import { saveVerse, getVerse } from './services/dbService';
import { encrypt, decrypt } from './services/cryptoService';

import ApiKeyManager from './components/ApiKeyManager';
import VerseSelector from './components/VerseSelector';
import TextDisplay from './components/TextDisplay';
import TtsControls from './components/TtsControls';
import History from './components/History';

const App: React.FC = () => {
  const [esvApiKey, setEsvApiKey] = useState<string>('');
  const [elevenLabsApiKey, setElevenLabsApiKey] = useState<string>('');
  const [humeApiKey, setHumeApiKey] = useState<string>('');
  const [keysLoaded, setKeysLoaded] = useState<boolean>(false);

  const [verseReference, setVerseReference] = useState<string>('John 3:16-17');
  const [verseGroups, setVerseGroups] = useState<ThemedVerseGroup[]>([]);
  const [ttsProvider, setTtsProvider] = useState<TtsProvider>(TtsProvider.Google);
  
  const [elevenLabsVoices, setElevenLabsVoices] = useState<VoiceOption[]>(TTS_VOICES[TtsProvider.ElevenLabs]);
  
  const allVoices = useMemo(() => ({
    ...TTS_VOICES,
    [TtsProvider.ElevenLabs]: elevenLabsVoices,
  }), [elevenLabsVoices]);

  const [selectedVoice, setSelectedVoice] = useState<string>(allVoices[TtsProvider.Google][0].id);
  const [speechRate, setSpeechRate] = useState<number>(1);
  const [speechPitch, setSpeechPitch] = useState<number>(0);

  const [isLoadingVerse, setIsLoadingVerse] = useState<boolean>(false);
  const [generatingAudioForVerse, setGeneratingAudioForVerse] = useState<Verse | null>(null);
  const [playingVerseRef, setPlayingVerseRef] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [playbackProgress, setPlaybackProgress] = useState<number>(0);
  const [playbackHistory, setPlaybackHistory] = useState<HistoryItem[]>([]);

  const audioContextRef = useRef<AudioContext | null>(null);
  const currentSourceNodeRef = useRef<AudioBufferSourceNode | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);
  const playbackStartTimeRef = useRef<number>(0);
  const playbackStartOffsetRef = useRef<number>(0);

  // Load and decrypt keys from localStorage on component mount
  useEffect(() => {
    const loadKeys = async () => {
        const storedEsv = localStorage.getItem('esvApiKey');
        const storedEleven = localStorage.getItem('elevenLabsApiKey');
        const storedHume = localStorage.getItem('humeApiKey');

        if (storedEsv) setEsvApiKey(await decrypt(storedEsv));
        if (storedEleven) setElevenLabsApiKey(await decrypt(storedEleven));
        if (storedHume) setHumeApiKey(await decrypt(storedHume));

        setKeysLoaded(true);
    };
    loadKeys();
  }, []);

  // Encrypt and save keys to localStorage when they change
  useEffect(() => {
    if (keysLoaded) {
      const save = async () => localStorage.setItem('esvApiKey', await encrypt(esvApiKey));
      save();
    }
  }, [esvApiKey, keysLoaded]);
  
  useEffect(() => {
    if (keysLoaded) {
      const save = async () => localStorage.setItem('elevenLabsApiKey', await encrypt(elevenLabsApiKey));
      save();
    }
  }, [elevenLabsApiKey, keysLoaded]);

  useEffect(() => {
    if (keysLoaded) {
      const save = async () => localStorage.setItem('humeApiKey', await encrypt(humeApiKey));
      save();
    }
  }, [humeApiKey, keysLoaded]);
  
  // Fetch ElevenLabs voices when API key changes
  useEffect(() => {
    const fetchVoices = async () => {
      if (elevenLabsApiKey) {
        try {
          const voices = await getElevenLabsVoices(elevenLabsApiKey);
          setElevenLabsVoices(voices.length > 0 ? voices : TTS_VOICES[TtsProvider.ElevenLabs]);
        } catch (err) {
          console.error("Failed to fetch ElevenLabs voices:", err);
          setError("Failed to fetch ElevenLabs voices. Using default list. Please check your API key.");
          setElevenLabsVoices(TTS_VOICES[TtsProvider.ElevenLabs]);
        }
      } else {
        // Revert to default if key is removed
        setElevenLabsVoices(TTS_VOICES[TtsProvider.ElevenLabs]);
      }
    };
    if (keysLoaded) {
        fetchVoices();
    }
  }, [elevenLabsApiKey, keysLoaded]);

  // Update selected voice when provider or available voices change
  useEffect(() => {
    const currentVoices = allVoices[ttsProvider];
    if (currentVoices && currentVoices.length > 0) {
      // Check if the currently selected voice is valid for the new provider
      if (!currentVoices.some(v => v.id === selectedVoice)) {
        setSelectedVoice(currentVoices[0].id);
      }
    }
  }, [ttsProvider, allVoices, selectedVoice]);

  // Initialize AudioContext on first user interaction (or component mount)
  useEffect(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }, []);

  // Load last session and history from storage on initial render
  useEffect(() => {
    const loadLastSession = async () => {
        const lastRefInput = localStorage.getItem('lastVerseReference');
        if (lastRefInput) {
            setVerseReference(lastRefInput);
        }

        const lastVerseGroupsJSON = localStorage.getItem('lastVerseGroups');
        if (!lastVerseGroupsJSON) return;

        try {
            const storedGroups: { theme: string; verseRefs: string[] }[] = JSON.parse(lastVerseGroupsJSON);
            setIsLoadingVerse(true);
            const loadedGroups: ThemedVerseGroup[] = [];

            for (const storedGroup of storedGroups) {
                const loadedVerses: Verse[] = [];
                for (const ref of storedGroup.verseRefs) {
                    const storedVerse = await getVerse(ref);
                    if (storedVerse) {
                        let verse: Verse = { reference: storedVerse.reference, text: storedVerse.text };
                        if (storedVerse.audio?.blob) {
                            try {
                                if (!audioContextRef.current) {
                                    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
                                }
                                const arrayBuffer = await storedVerse.audio.blob.arrayBuffer();
                                const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer);
                                verse.audio = {
                                    buffer: audioBuffer,
                                    provider: storedVerse.audio.provider,
                                    voiceName: storedVerse.audio.voiceName,
                                    duration: audioBuffer.duration,
                                };
                            } catch(decodeErr) {
                                console.error(`Failed to decode stored audio for ${ref}:`, decodeErr);
                            }
                        }
                        loadedVerses.push(verse);
                    } else {
                        console.warn(`Verse "${ref}" from last session not found in DB.`);
                    }
                }
                if (loadedVerses.length > 0) {
                    loadedGroups.push({ theme: storedGroup.theme, verses: loadedVerses });
                }
            }
            setVerseGroups(loadedGroups);
        } catch (err) {
            console.error('Failed to load last session:', err);
            setError('Could not restore the previous session.');
            localStorage.removeItem('lastVerseGroups');
        } finally {
            setIsLoadingVerse(false);
        }
    };
    
    const loadHistory = () => {
        const storedHistory = localStorage.getItem('playbackHistory');
        if (storedHistory) {
            try {
                setPlaybackHistory(JSON.parse(storedHistory));
            } catch (err) {
                console.error("Failed to parse playback history:", err);
                localStorage.removeItem('playbackHistory');
            }
        }
    };

    loadLastSession();
    loadHistory();
  }, []);


    const performVerseFetch = useCallback(async (textInput: string) => {
        if (!esvApiKey) {
            setError('Please enter your ESV API key.');
            return;
        }
        const trimmedReference = textInput.trim();
        if (!trimmedReference) {
            setError('Please enter a theme and Bible reference.');
            return;
        }

        setIsLoadingVerse(true);
        setError(null);
        setVerseGroups([]);

        try {
            const lines = trimmedReference.split('\n').filter(line => line.trim() !== '');
            if (lines.length === 0) {
                setError("Please enter a theme and verse references.");
                setIsLoadingVerse(false);
                return;
            }
            
            const parsedGroups: { theme: string; verseRefs: string[] }[] = [];
            let currentGroup: { theme: string; verseRefs: string[] } | null = null;
            
            for (const line of lines) {
                // Heuristic: if a line contains digits, it's a verse reference. Otherwise, it's a theme.
                if (/\d/.test(line)) {
                    if (currentGroup) {
                        currentGroup.verseRefs.push(line.trim());
                    } else {
                        // Verse before a theme is not allowed
                        setError("Input must start with a theme. A theme is a line without numbers, like 'The Gospel'.");
                        setIsLoadingVerse(false);
                        return;
                    }
                } else { // It's a theme
                    if (currentGroup && currentGroup.verseRefs.length > 0) {
                        parsedGroups.push(currentGroup);
                    }
                    currentGroup = { theme: line.trim(), verseRefs: [] };
                }
            }

            if (currentGroup && currentGroup.verseRefs.length > 0) {
                parsedGroups.push(currentGroup);
            }
            
            if (parsedGroups.length === 0) {
                 if(currentGroup) {
                     setError(`Please provide verse references for the theme "${currentGroup.theme}". A verse reference should contain numbers (e.g., John 3:16).`);
                } else {
                    setError("No valid themes and verses found. Input should start with a theme (a line without numbers).");
                }
                setIsLoadingVerse(false);
                return;
            }

            const newVerseGroups: ThemedVerseGroup[] = [];
            for (const group of parsedGroups) {
                const verseRefsString = group.verseRefs.join(',');
                if (verseRefsString) {
                    const fetchedVerses = await fetchVerse(verseRefsString, esvApiKey);
                    newVerseGroups.push({ theme: group.theme, verses: fetchedVerses });
                }
            }
            
            const groupsToStore = newVerseGroups.map(group => ({
                theme: group.theme,
                verseRefs: group.verses.map(v => v.reference)
            }));

            localStorage.setItem('lastVerseGroups', JSON.stringify(groupsToStore));
            localStorage.setItem('lastVerseReference', textInput);
            
            for (const group of newVerseGroups) {
                for (const verse of group.verses) {
                    const existingVerse = await getVerse(verse.reference);
                    await saveVerse({
                        reference: verse.reference,
                        text: verse.text,
                        audio: existingVerse?.audio,
                    });
                }
            }

            setVerseGroups(newVerseGroups);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An unknown error occurred.');
        } finally {
            setIsLoadingVerse(false);
        }
    }, [esvApiKey]);

    const handleFetchVerse = useCallback(async () => {
        await performVerseFetch(verseReference);
    }, [verseReference, performVerseFetch]);
  
    const handleGenerateAudio = useCallback(async (verseToGenerate: Verse) => {
        if (!verseToGenerate.text) {
        setError('Cannot read an empty verse.');
        return;
        }
        if (!audioContextRef.current) {
        audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        }

        setGeneratingAudioForVerse(verseToGenerate);
        setError(null);

        try {
        const apiKeys = {
            [TtsProvider.ElevenLabs]: elevenLabsApiKey,
            [TtsProvider.HumeAI]: humeApiKey,
        };

        const audioArrayBuffer = await generateSpeech(verseToGenerate.text, ttsProvider, selectedVoice, apiKeys);

        if (audioArrayBuffer) {
            await audioContextRef.current.resume();
            
            let preliminaryAudioBuffer: AudioBuffer;
            if (ttsProvider === TtsProvider.Google) {
            const pcmData = new Uint8Array(audioArrayBuffer);
            preliminaryAudioBuffer = await decodePcmAudioData(pcmData, audioContextRef.current);
            } else {
            preliminaryAudioBuffer = await audioContextRef.current.decodeAudioData(audioArrayBuffer);
            }

            const wavBlob = bufferToWave(preliminaryAudioBuffer);
            
            const finalArrayBuffer = await wavBlob.arrayBuffer();
            const audioBuffer = await audioContextRef.current.decodeAudioData(finalArrayBuffer);

            const voiceName = allVoices[ttsProvider].find(v => v.id === selectedVoice)?.name || selectedVoice;
            
            await saveVerse({
                reference: verseToGenerate.reference,
                text: verseToGenerate.text,
                audio: {
                    blob: wavBlob,
                    provider: ttsProvider,
                    voiceName: voiceName,
                    duration: audioBuffer.duration,
                },
            });

            const newAudio: GeneratedAudio = {
            buffer: audioBuffer,
            provider: ttsProvider,
            voiceName: voiceName,
            duration: audioBuffer.duration,
            };

            setVerseGroups(currentGroups =>
            currentGroups.map(group => ({
                ...group,
                verses: group.verses.map(v => 
                v.reference === verseToGenerate.reference ? { ...v, audio: newAudio } : v
                )
            }))
            );
        }
        } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to generate audio. Check the browser console for more details.');
        } finally {
        setGeneratingAudioForVerse(null);
        }
    }, [ttsProvider, selectedVoice, elevenLabsApiKey, humeApiKey, allVoices]);

    const updateProgress = useCallback(() => {
        if (!audioContextRef.current || !currentSourceNodeRef.current || !playingVerseRef) {
            return;
        }

        const playingVerse = verseGroups.flatMap(g => g.verses).find(v => v.reference === playingVerseRef);
        if (!playingVerse?.audio) return;

        const duration = playingVerse.audio.duration;
        const elapsedTime = (audioContextRef.current.currentTime - playbackStartTimeRef.current) + playbackStartOffsetRef.current;
        const progress = Math.min((elapsedTime / duration) * 100, 100);
        
        setPlaybackProgress(progress);

        animationFrameIdRef.current = requestAnimationFrame(updateProgress);
    }, [playingVerseRef, verseGroups]);

    const addToHistory = useCallback((verse: Verse, theme: string) => {
        const newItem: HistoryItem = {
            theme,
            reference: verse.reference,
            playedAt: Date.now(),
        };

        setPlaybackHistory(prevHistory => {
            const filteredHistory = prevHistory.filter(item => item.reference !== newItem.reference);
            const updatedHistory = [newItem, ...filteredHistory];
            const finalHistory = updatedHistory.slice(0, 20); // Cap at 20 items
            localStorage.setItem('playbackHistory', JSON.stringify(finalHistory));
            return finalHistory;
        });
    }, []);

    const handlePlayPause = useCallback((verseRef: string) => {
        if (currentSourceNodeRef.current) {
            currentSourceNodeRef.current.onended = null;
            currentSourceNodeRef.current.stop();
            currentSourceNodeRef.current = null;
        }
        if (animationFrameIdRef.current) {
            cancelAnimationFrame(animationFrameIdRef.current);
            animationFrameIdRef.current = null;
        }

        if (playingVerseRef === verseRef) {
            setPlayingVerseRef(null);
            setPlaybackProgress(0);
            return;
        }
        
        let verseForHistory: Verse | undefined;
        let themeForHistory: string | undefined;
        for (const group of verseGroups) {
            const foundVerse = group.verses.find(v => v.reference === verseRef);
            if (foundVerse) {
                verseForHistory = foundVerse;
                themeForHistory = group.theme;
                break;
            }
        }
        if (verseForHistory && themeForHistory) {
            addToHistory(verseForHistory, themeForHistory);
        }

        const verse = verseGroups.flatMap(g => g.verses).find(v => v.reference === verseRef);
        if (verse?.audio?.buffer && audioContextRef.current) {
            audioContextRef.current.resume();
            const source = audioContextRef.current.createBufferSource();
            source.buffer = verse.audio.buffer;
            
            source.playbackRate.value = speechRate;
            source.detune.value = speechPitch;
            
            source.connect(audioContextRef.current.destination);
            source.start(0);
            
            playbackStartTimeRef.current = audioContextRef.current.currentTime;
            playbackStartOffsetRef.current = 0;

            source.onended = () => {
                if (playingVerseRef === verseRef) {
                    setPlayingVerseRef(null);
                    setPlaybackProgress(0);
                }
                if (animationFrameIdRef.current) {
                    cancelAnimationFrame(animationFrameIdRef.current);
                    animationFrameIdRef.current = null;
                }
                if (currentSourceNodeRef.current === source) {
                    currentSourceNodeRef.current = null;
                }
            };

            currentSourceNodeRef.current = source;
            setPlayingVerseRef(verseRef);
            animationFrameIdRef.current = requestAnimationFrame(updateProgress);
        }
    }, [verseGroups, playingVerseRef, speechRate, speechPitch, updateProgress, addToHistory]);

    const handleSeek = useCallback((verseRef: string, newProgress: number) => { // newProgress is 0-1
        const verse = verseGroups.flatMap(g => g.verses).find(v => v.reference === verseRef);
        if (!verse?.audio?.buffer || !audioContextRef.current) return;

        if (currentSourceNodeRef.current) {
            currentSourceNodeRef.current.onended = null;
            currentSourceNodeRef.current.stop();
            currentSourceNodeRef.current = null;
        }
        if (animationFrameIdRef.current) {
            cancelAnimationFrame(animationFrameIdRef.current);
            animationFrameIdRef.current = null;
        }
        
        const duration = verse.audio.duration;
        const seekTime = duration * newProgress;
        setPlaybackProgress(newProgress * 100);

        audioContextRef.current.resume();
        const source = audioContextRef.current.createBufferSource();
        source.buffer = verse.audio.buffer;
        source.playbackRate.value = speechRate;
        source.detune.value = speechPitch;
        source.connect(audioContextRef.current.destination);
        source.start(0, seekTime);

        playbackStartTimeRef.current = audioContextRef.current.currentTime;
        playbackStartOffsetRef.current = seekTime;

        source.onended = () => {
            if (playingVerseRef === verseRef) {
                setPlayingVerseRef(null);
                setPlaybackProgress(0);
            }
            if (animationFrameIdRef.current) {
                cancelAnimationFrame(animationFrameIdRef.current);
                animationFrameIdRef.current = null;
            }
            if (currentSourceNodeRef.current === source) {
                currentSourceNodeRef.current = null;
            }
        };

        currentSourceNodeRef.current = source;
        setPlayingVerseRef(verseRef);
        animationFrameIdRef.current = requestAnimationFrame(updateProgress);
    }, [verseGroups, speechRate, speechPitch, updateProgress, playingVerseRef]);

    const handleRevisitFromHistory = useCallback(async (item: HistoryItem) => {
        const newReference = `${item.theme}\n${item.reference}`;
        setVerseReference(newReference);
        await performVerseFetch(newReference);
    }, [performVerseFetch]);

    const handleClearHistory = useCallback(() => {
        setPlaybackHistory([]);
        localStorage.removeItem('playbackHistory');
    }, []);

    return (
        <div className="min-h-screen bg-brand-bg flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8">
        <div className="w-full max-w-2xl mx-auto space-y-8">
            <header className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold text-brand-primary font-serif">
                Audio Bible Reader
            </h1>
            <p className="mt-2 text-lg text-brand-text-muted">
                Fetch ESV passages and listen with AI-powered voices.
            </p>
            </header>

            <main className="bg-brand-surface p-6 sm:p-8 rounded-2xl shadow-2xl space-y-6">
            <ApiKeyManager
                esvApiKey={esvApiKey}
                setEsvApiKey={setEsvApiKey}
                elevenLabsApiKey={elevenLabsApiKey}
                setElevenLabsApiKey={setElevenLabsApiKey}
                humeApiKey={humeApiKey}
                setHumeApiKey={setHumeApiKey}
            />
            
            <div className="border-t border-white/10 my-6"></div>

            <VerseSelector
                verseReference={verseReference}
                setVerseReference={setVerseReference}
                onFetch={handleFetchVerse}
                isLoading={isLoadingVerse}
            />
            
            {error && <div className="bg-red-900/50 text-red-300 border border-red-700 p-3 rounded-lg text-sm">{error}</div>}

            <TextDisplay
                verseGroups={verseGroups}
                isLoading={isLoadingVerse}
                onGenerateAudio={handleGenerateAudio}
                generatingAudioForVerse={generatingAudioForVerse}
                onPlayPause={handlePlayPause}
                playingVerseRef={playingVerseRef}
                playbackProgress={playbackProgress}
                onSeek={handleSeek}
            />

            {verseGroups.length > 0 && (
                <>
                <div className="border-t border-white/10 my-6"></div>
                <TtsControls
                    selectedProvider={ttsProvider}
                    setSelectedProvider={setTtsProvider}
                    availableVoices={allVoices[ttsProvider]}
                    selectedVoice={selectedVoice}
                    setSelectedVoice={setSelectedVoice}
                    speechRate={speechRate}
                    setSpeechRate={setSpeechRate}
                    speechPitch={speechPitch}
                    setSpeechPitch={setSpeechPitch}
                />
                </>
            )}
            </main>
            
            {playbackHistory.length > 0 && (
                <History
                    history={playbackHistory}
                    onRevisit={handleRevisitFromHistory}
                    onClear={handleClearHistory}
                />
            )}

            <footer className="text-center text-brand-text-muted text-sm">
                <p>&copy; {new Date().getFullYear()} Audio Bible Reader. All rights reserved.</p>
            </footer>
        </div>
        </div>
    );
};

export default App;