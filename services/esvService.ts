import { Verse } from '../types';

/**
 * Normalizes verse reference by replacing en-dashes and em-dashes with hyphens.
 * @param reference The raw verse reference string.
 * @returns A normalized reference string.
 */
const normalizeReference = (reference: string): string => {
  return reference.replace(/[\u2013\u2014]/g, '-');
};

/**
 * Fetches Bible passages from the ESV API.
 * Handles multiple passages separated by commas or newlines and returns a structured array.
 * @param reference - The Bible verse reference (e.g., "John 3:16-17, Romans 8:28").
 * @param apiKey - The user's ESV API key.
 * @returns A promise that resolves to an array of Verse objects.
 */
export const fetchVerse = async (reference: string, apiKey: string): Promise<Verse[]> => {
  const processedReference = reference
    .replace(/\n/g, ',')
    .split(',')
    .map(ref => ref.trim())
    .filter(Boolean)
    .join(';');

  const normalizedRef = normalizeReference(processedReference);
  const encodedReference = encodeURIComponent(normalizedRef);
  const url = `https://api.esv.org/v3/passage/text/?q=${encodedReference}&include-headings=false&include-footnotes=false&include-verse-numbers=true&include-short-copyright=false&include-passage-references=true`;

  try {
    const response = await fetch(url, {
      headers: {
        'Authorization': `Token ${apiKey}`,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      if (errorData && errorData.detail) {
        throw new Error(`ESV API Error: ${errorData.detail}`);
      }
      throw new Error(`Failed to fetch from ESV API. Status: ${response.status}`);
    }

    const data = await response.json();
    
    if (data.passages && data.passages.length > 0) {
      return data.passages.map((passageContent: string) => {
        const lines = passageContent.trim().split('\n');
        // The first line is the reference
        const reference = lines.shift()?.trim() || 'Unknown Reference';
        // The rest is the text. Remove verse numbers like [16] and extra whitespace.
        const text = lines.join(' ').replace(/\[\d+\]/g, ' ').replace(/\s+/g, ' ').trim();
        return { reference, text };
      });
    } else {
      throw new Error('Invalid reference or no passage found. Please check your input.');
    }
  } catch (error) {
    console.error('Error fetching verse:', error);
    if (error instanceof TypeError && error.message.includes("Failed to construct 'Request'")) {
        throw new Error('The API key appears to contain invalid characters. Please ensure it is copied correctly without any special symbols or extra spaces.');
    }
    if (error instanceof Error) {
        throw error;
    }
    throw new Error('An unexpected error occurred while fetching the verse.');
  }
};