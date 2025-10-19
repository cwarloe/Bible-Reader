import React from 'react';
import Spinner from './Spinner';

interface VerseSelectorProps {
  verseReference: string;
  setVerseReference: (ref: string) => void;
  onFetch: () => void;
  isLoading: boolean;
}

const VerseSelector: React.FC<VerseSelectorProps> = ({
  verseReference,
  setVerseReference,
  onFetch,
  isLoading,
}) => {
  const handleTextAreaKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onFetch();
    }
  };

  const exampleTopicalSystem = `Introductions - Church Epistles
Romans 1:1-7
1 Corinthians 1:1-3
2 Corinthians 1:1-3
Galatians 1:1-5
Ephesians 1:1-2
Philippians 1:1-2
Colossians 1:1-2
1 Thessalonians 1:1
2 Thessalonians 1:1-2

Introductions - Pastoral Epistles
1 Timothy 1:1-2
2 Timothy 1:1-2
Titus 1:1-4`;

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="verse-reference" className="block text-sm font-medium text-brand-text-muted mb-2">
          Bible Reference (by Topic)
        </label>
        <div className="flex flex-col sm:flex-row gap-4">
          <textarea
            id="verse-reference"
            rows={4}
            value={verseReference}
            onChange={(e) => setVerseReference(e.target.value)}
            onKeyDown={handleTextAreaKeyDown}
            placeholder={`Theme 1\nVerse Ref 1\nVerse Ref 2\n\nTheme 2\nVerse Ref 3`}
            className="flex-grow bg-brand-bg border border-white/20 text-brand-text rounded-md px-3 py-2 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition duration-150 ease-in-out resize-y"
            disabled={isLoading}
          />
          <button
            onClick={onFetch}
            disabled={isLoading}
            className="flex items-center justify-center px-6 py-2 bg-brand-primary text-brand-bg font-bold rounded-md hover:bg-brand-secondary disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors duration-200 ease-in-out self-start sm:self-stretch"
          >
            {isLoading ? <Spinner /> : 'Fetch'}
          </button>
        </div>
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          <span className="text-xs text-brand-text-muted self-center">Need an idea?</span>
          <button 
            onClick={() => setVerseReference(exampleTopicalSystem)} 
            className="text-xs bg-white/10 hover:bg-white/20 text-brand-text-muted px-2 py-1 rounded-md transition-colors"
          >
            Load Topical Memory System example
          </button>
        </div>
      </div>
    </div>
  );
};

export default VerseSelector;