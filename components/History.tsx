import React from 'react';
import { HistoryItem } from '../types';

interface HistoryProps {
  history: HistoryItem[];
  onRevisit: (item: HistoryItem) => void;
  onClear: () => void;
}

const HistoryIcon: React.FC = () => (
    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 inline-block" viewBox="0 0 20 20" fill="currentColor">
        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.707-10.293a1 1 0 00-1.414-1.414l-3 3a1 1 0 000 1.414l3 3a1 1 0 001.414-1.414L9.414 11H13a1 1 0 100-2H9.414l1.293-1.293z" clipRule="evenodd" />
    </svg>
);

const History: React.FC<HistoryProps> = ({ history, onRevisit, onClear }) => {
  return (
    <div className="w-full max-w-2xl mx-auto bg-brand-surface p-6 sm:p-8 rounded-2xl shadow-2xl">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-brand-primary font-serif flex items-center">
            <HistoryIcon />
            Playback History
        </h2>
        <button
          onClick={onClear}
          className="text-xs text-brand-text-muted hover:text-brand-text underline transition-colors"
        >
          Clear History
        </button>
      </div>
      <ul className="space-y-2 max-h-60 overflow-y-auto pr-2 -mr-2">
        {history.map((item) => (
          <li key={item.playedAt}>
            <button
              onClick={() => onRevisit(item)}
              className="w-full text-left p-3 bg-brand-bg rounded-lg hover:bg-white/10 transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              aria-label={`Revisit ${item.theme}: ${item.reference}`}
            >
              <p className="font-semibold text-brand-secondary text-sm truncate">{item.theme}</p>
              <p className="text-brand-text-muted text-sm">{item.reference}</p>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default History;
