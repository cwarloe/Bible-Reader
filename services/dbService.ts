import { TtsProvider } from '../types';

// This interface is specific to what we store in IndexedDB
export interface StoredAudio {
  blob: Blob;
  provider: TtsProvider;
  voiceName: string;
  duration: number;
}

export interface StoredVerse {
  reference: string;
  text: string;
  audio?: StoredAudio;
}

const DB_NAME = 'AudioBibleDB';
const DB_VERSION = 1;
const STORE_NAME = 'verses';

let dbPromise: Promise<IDBDatabase> | null = null;

/**
 * Initializes and returns a singleton instance of the IndexedDB database connection.
 * This ensures that generated audio and verse text can be cached locally and
 * persist across browser sessions, preventing redundant API calls.
 */
const getDb = (): Promise<IDBDatabase> => {
    if (!dbPromise) {
        dbPromise = new Promise((resolve, reject) => {
            const request = indexedDB.open(DB_NAME, DB_VERSION);

            request.onerror = () => {
                console.error('Database error:', request.error);
                reject('Error opening database');
                dbPromise = null;
            };

            request.onsuccess = () => {
                resolve(request.result);
            };

            request.onupgradeneeded = (event) => {
                const db = (event.target as IDBOpenDBRequest).result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: 'reference' });
                }
            };
        });
    }
    return dbPromise;
};

/**
 * Saves a verse, including its text and any generated audio, to the local IndexedDB.
 * This is the core of the audio caching mechanism.
 * @param verse The verse object to save.
 */
export const saveVerse = async (verse: StoredVerse): Promise<void> => {
  const db = await getDb();
  const transaction = db.transaction(STORE_NAME, 'readwrite');
  const store = transaction.objectStore(STORE_NAME);
  store.put(verse);
  return new Promise((resolve, reject) => {
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
};

/**
 * Retrieves a verse from the local IndexedDB cache by its reference.
 * This is used to load previously fetched/generated content when the app starts.
 * @param reference The Bible reference (e.g., "John 3:16") to look up.
 * @returns The stored verse, or undefined if not found.
 */
export const getVerse = async (reference: string): Promise<StoredVerse | undefined> => {
  const db = await getDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(STORE_NAME, 'readonly');
    const store = transaction.objectStore(STORE_NAME);
    const request = store.get(reference);

    request.onsuccess = () => resolve(request.result);
    request.onerror = () => {
      console.error('Error getting verse:', request.error);
      reject(request.error);
    };
  });
};
