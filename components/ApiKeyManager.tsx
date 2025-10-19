import React from 'react';

interface ApiKeyManagerProps {
  esvApiKey: string;
  setEsvApiKey: (key: string) => void;
  elevenLabsApiKey: string;
  setElevenLabsApiKey: (key: string) => void;
  humeApiKey: string;
  setHumeApiKey: (key: string) => void;
}

const ApiKeyManager: React.FC<ApiKeyManagerProps> = ({
  esvApiKey,
  setEsvApiKey,
  elevenLabsApiKey,
  setElevenLabsApiKey,
  humeApiKey,
  setHumeApiKey,
}) => {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold text-brand-text">API Keys</h2>
        <p className="text-sm text-brand-text-muted">
          Your keys are stored in your browser's local storage and are never sent to our servers.
          Google Gemini TTS uses the environment API key.
        </p>
      </div>

      {/* ESV API Key */}
      <div>
        <label htmlFor="esv-api-key" className="block text-sm font-medium text-brand-text-muted mb-2">
          ESV API Key (for fetching scripture)
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            id="esv-api-key"
            type="password"
            value={esvApiKey}
            onChange={(e) => setEsvApiKey(e.target.value)}
            placeholder="Enter your ESV API key"
            className="flex-grow bg-brand-bg border border-white/20 text-brand-text rounded-md px-3 py-2 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition duration-150 ease-in-out"
          />
          <a href="https://api.esv.org/account/create-application/" target="_blank" rel="noopener noreferrer" className="text-center sm:text-left text-sm text-brand-primary hover:text-brand-secondary underline whitespace-nowrap pt-2">
            Get a key
          </a>
        </div>
      </div>
      
      {/* ElevenLabs API Key */}
      <div>
        <label htmlFor="elevenlabs-api-key" className="block text-sm font-medium text-brand-text-muted mb-2">
          ElevenLabs API Key (optional)
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            id="elevenlabs-api-key"
            type="password"
            value={elevenLabsApiKey}
            onChange={(e) => setElevenLabsApiKey(e.target.value)}
            placeholder="Enter your ElevenLabs API key"
            className="flex-grow bg-brand-bg border border-white/20 text-brand-text rounded-md px-3 py-2 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition duration-150 ease-in-out"
          />
           <a href="https://elevenlabs.io/" target="_blank" rel="noopener noreferrer" className="text-center sm:text-left text-sm text-brand-primary hover:text-brand-secondary underline whitespace-nowrap pt-2">
            Get a key
          </a>
        </div>
      </div>

      {/* Hume AI API Key */}
      <div>
        <label htmlFor="hume-api-key" className="block text-sm font-medium text-brand-text-muted mb-2">
          Hume AI API Key (optional)
        </label>
        <div className="flex flex-col sm:flex-row gap-2">
          <input
            id="hume-api-key"
            type="password"
            value={humeApiKey}
            onChange={(e) => setHumeApiKey(e.target.value)}
            placeholder="Enter your Hume AI API key"
            className="flex-grow bg-brand-bg border border-white/20 text-brand-text rounded-md px-3 py-2 focus:ring-2 focus:ring-brand-primary focus:border-brand-primary transition duration-150 ease-in-out"
          />
           <a href="https://hume.ai/" target="_blank" rel="noopener noreferrer" className="text-center sm:text-left text-sm text-brand-primary hover:text-brand-secondary underline whitespace-nowrap pt-2">
            Get a key
          </a>
        </div>
      </div>
    </div>
  );
};

export default ApiKeyManager;