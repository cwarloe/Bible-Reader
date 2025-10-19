const KEY_NAME = 'audio-bible-encryption-key';
const ALGORITHM = { name: 'AES-GCM', length: 256 };
const IV_LENGTH = 12; // bytes for AES-GCM

let cryptoKey: CryptoKey | null = null;

/**
 * Retrieves the encryption key from storage, or generates and stores a new one.
 */
const getKey = async (): Promise<CryptoKey> => {
    if (cryptoKey) {
        return cryptoKey;
    }

    const storedKey = localStorage.getItem(KEY_NAME);
    if (storedKey) {
        try {
            const jwk = JSON.parse(storedKey);
            cryptoKey = await window.crypto.subtle.importKey(
                'jwk',
                jwk,
                ALGORITHM,
                true,
                ['encrypt', 'decrypt']
            );
            return cryptoKey;
        } catch (e) {
            console.error("Failed to import stored key, generating a new one.", e);
        }
    }

    // If no valid key found, generate a new one
    const newKey = await window.crypto.subtle.generateKey(
        ALGORITHM,
        true, // extractable
        ['encrypt', 'decrypt']
    );

    const jwk = await window.crypto.subtle.exportKey('jwk', newKey);
    localStorage.setItem(KEY_NAME, JSON.stringify(jwk));
    cryptoKey = newKey;
    return cryptoKey;
};

/**
 * Encrypts a plaintext string.
 * @param plaintext The string to encrypt.
 * @returns A promise that resolves to a base64 encoded string containing the IV and ciphertext.
 */
export const encrypt = async (plaintext: string): Promise<string> => {
    if (!plaintext) return '';
    try {
        const key = await getKey();
        const iv = window.crypto.getRandomValues(new Uint8Array(IV_LENGTH));
        const encoded = new TextEncoder().encode(plaintext);

        const ciphertext = await window.crypto.subtle.encrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            encoded
        );

        // Combine IV and ciphertext for storage
        const combined = new Uint8Array(iv.length + ciphertext.byteLength);
        combined.set(iv, 0);
        combined.set(new Uint8Array(ciphertext), iv.length);

        // Convert to base64 to store in localStorage
        return btoa(String.fromCharCode.apply(null, Array.from(combined)));
    } catch (e) {
        console.error("Encryption failed:", e);
        // Fallback to plaintext if encryption fails to avoid breaking the app
        return plaintext;
    }
};

/**
 * Decrypts a base64 encoded string.
 * @param encryptedBase64 The base64 string containing IV and ciphertext.
 * @returns A promise that resolves to the decrypted plaintext string.
 */
export const decrypt = async (encryptedBase64: string): Promise<string> => {
    if (!encryptedBase64) return '';
    try {
        const key = await getKey();
        // Decode from base64
        const combined = new Uint8Array(Array.from(atob(encryptedBase64), c => c.charCodeAt(0)));
        
        const iv = combined.slice(0, IV_LENGTH);
        const ciphertext = combined.slice(IV_LENGTH);

        const decrypted = await window.crypto.subtle.decrypt(
            { name: 'AES-GCM', iv: iv },
            key,
            ciphertext
        );

        return new TextDecoder().decode(decrypted);
    } catch (e) {
        console.error("Decryption failed:", e);
        // If decryption fails, it might be an old plaintext key. Return it as is.
        return encryptedBase64;
    }
};
