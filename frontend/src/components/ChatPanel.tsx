import { useState, useRef, useEffect } from 'react';
import type { EditPlan } from '../types';
import { reasoningApi } from '../api';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  plan?: EditPlan;
  error?: string;
};

type Props = {
  documentId: string | null;
  onEditsApplied: () => void;
};

export function ChatPanel({ documentId, onEditsApplied }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async () => {
    const instruction = input.trim();
    if (!instruction || loading) return;

    setInput('');
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: instruction },
    ]);
    setLoading(true);

    try {
      const data = await reasoningApi.execute(instruction, documentId);

      const chapters = data.relevant_chapters as number[] | undefined;
      const ops = data.operations_performed as number | undefined;
      const reasoning = data.reasoning as string | undefined;
      const planOpCount = data.edit_plan?.operations?.length ?? 0;

      let reply: string;
      if (chapters && chapters.length > 0) {
        reply = `Done. I reviewed chapter ${chapters.join(', ')} and performed ${ops ?? planOpCount ?? 0} operation(s).`;
        if (reasoning) reply += `\n\nReasoning: ${reasoning}`;
      } else if (planOpCount > 0) {
        reply = `Done. I prepared and applied ${planOpCount} planned edit(s).`;
      } else {
        reply = data.reasoning
          ? `No chapters needed changes for this instruction.\n\n${data.reasoning}`
          : "I couldn't find specific content to change for that instruction. Try referring to scenes or themes in your document.";
      }

      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: reply,
          plan: data.edit_plan,
        },
      ]);
      onEditsApplied();
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: '',
          error: err instanceof Error ? err.message : 'Request failed',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-panel-strong flex h-full w-[24rem] flex-col overflow-hidden rounded-[32px]">
      <div className="border-b border-[var(--border)] px-5 py-5">
        <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
          AI Copilot
        </p>
        <h2 className="mt-1 text-lg font-semibold text-[var(--ink)]">Editor Assistant</h2>
        <p className="mt-2 text-xs leading-6 text-[var(--muted)]">
          {documentId
            ? 'Uses chapter summaries for retrieval, then plans localized chapter/paragraph/line edits.'
            : 'Select a project first so the AI can traverse your document.'}
        </p>
      </div>
      <div className="flex-1 overflow-auto px-4 py-4 space-y-3">
        {messages.length === 0 && (
          <div className="glass-panel rounded-[28px] px-4 py-5 text-sm text-[var(--muted)] leading-7">
            Ask the AI to edit your story. It will retrieve relevant chapters, plan localized
            edits, and apply them.
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`rounded-[24px] px-4 py-3 text-sm shadow-sm ${
              m.role === 'user'
                ? 'premium-button ml-8'
                : 'glass-panel mr-8 text-[var(--ink)]'
            }`}
          >
            {m.error ? (
              <p className="text-red-600 dark:text-red-400">{m.error}</p>
            ) : (
              <p className="whitespace-pre-wrap leading-7">{m.content}</p>
            )}
            {m.plan?.operations?.length ? (
              <p className="mt-3 text-xs opacity-80">
                Planned operations: {m.plan.operations.map((t) => t.operation).join(', ')}
              </p>
            ) : null}
          </div>
        ))}
        {loading && (
          <div className="glass-panel mr-8 rounded-[24px] px-4 py-3 text-sm">
            <p className="text-[var(--muted)]">Applying your edits…</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-[var(--border)] px-4 py-4">
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded-2xl border border-[var(--border)] bg-[var(--paper-strong)] px-4 py-3 text-sm outline-none focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]"
            placeholder="e.g. Make the storm scene more intense"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && send()}
            disabled={loading || !documentId}
          />
          <button
            type="button"
            onClick={send}
            disabled={loading || !input.trim() || !documentId}
            className="premium-button rounded-2xl px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}
