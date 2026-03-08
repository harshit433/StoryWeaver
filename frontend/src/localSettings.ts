export const GROQ_API_KEY_STORAGE_KEY = 'writer.groqApiKey';

export function getStoredGroqApiKey(): string {
  if (typeof window === 'undefined') return '';
  return window.localStorage.getItem(GROQ_API_KEY_STORAGE_KEY)?.trim() || '';
}

export function setStoredGroqApiKey(apiKey: string): void {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(GROQ_API_KEY_STORAGE_KEY, apiKey.trim());
}

export function clearStoredGroqApiKey(): void {
  if (typeof window === 'undefined') return;
  window.localStorage.removeItem(GROQ_API_KEY_STORAGE_KEY);
}

export function getGroqApiKeyPreview(): string | null {
  const apiKey = getStoredGroqApiKey();
  if (!apiKey) return null;
  if (apiKey.length <= 8) return '*'.repeat(apiKey.length);
  return `${apiKey.slice(0, 4)}${'*'.repeat(apiKey.length - 8)}${apiKey.slice(-4)}`;
}
