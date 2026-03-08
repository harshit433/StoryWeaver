import { useEffect, useState } from 'react';
import {
  clearStoredGroqApiKey,
  getGroqApiKeyPreview,
  getStoredGroqApiKey,
  setStoredGroqApiKey,
} from '../localSettings';

type Props = {
  open: boolean;
  onClose: () => void;
  onSaved?: () => void;
};

export function SettingsDialog({ open, onClose, onSaved }: Props) {
  const [apiKey, setApiKey] = useState('');
  const [preview, setPreview] = useState<string | null>(null);
  const [hasKey, setHasKey] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setError(null);
    setMessage(null);
    const storedKey = getStoredGroqApiKey();
    setHasKey(Boolean(storedKey));
    setPreview(getGroqApiKeyPreview());
  }, [open]);

  if (!open) return null;

  const handleSave = async () => {
    if (!apiKey.trim()) return;
    setError(null);
    setMessage(null);
    try {
      setStoredGroqApiKey(apiKey.trim());
      setHasKey(true);
      setPreview(getGroqApiKeyPreview());
      setApiKey('');
      setMessage('Groq API key saved in this browser only.');
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save API key');
    }
  };

  const handleClear = async () => {
    setError(null);
    setMessage(null);
    try {
      clearStoredGroqApiKey();
      setHasKey(false);
      setPreview(null);
      setApiKey('');
      setMessage('Groq API key removed from this browser.');
      onSaved?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear API key');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/35 px-4 backdrop-blur-md">
      <div className="glass-panel-strong w-full max-w-xl rounded-[32px] p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Settings
            </p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]">
              AI Provider Configuration
            </h2>
            <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
              Add your own Groq API key. It is stored only in this browser and sent with your requests.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--muted)] hover:bg-white/10"
          >
            Close
          </button>
        </div>

        <div className="mt-6 rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Current Key
          </p>
          <p className="mt-2 text-sm text-[var(--ink)]">
            {hasKey
              ? `Configured (${preview ?? 'saved'})`
              : 'No Groq API key saved in this browser yet.'}
          </p>
        </div>

        <div className="mt-4">
          <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
            Groq API Key
          </label>
          <input
            type="password"
            className="w-full rounded-2xl border border-[var(--border)] bg-[var(--paper-strong)] px-4 py-3 text-sm outline-none focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]"
            placeholder="gsk_..."
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            autoFocus
          />
        </div>

        {message && (
          <p className="mt-4 rounded-2xl border border-emerald-400/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-700 dark:text-emerald-300">
            {message}
          </p>
        )}
        {error && (
          <p className="mt-4 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300">
            {error}
          </p>
        )}

        <div className="mt-6 flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleSave}
            disabled={!apiKey.trim()}
            className="premium-button rounded-2xl px-5 py-3 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
          >
            Save API Key
          </button>
          <button
            type="button"
            onClick={handleClear}
            disabled={!hasKey}
            className="rounded-2xl border border-[var(--border)] px-5 py-3 text-sm text-[var(--muted)] hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Remove Key
          </button>
        </div>
      </div>
    </div>
  );
}
