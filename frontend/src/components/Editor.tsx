import { useState, useEffect } from 'react';
import type { TreeNode } from '../types';
import { projectApi } from '../api';

type Props = {
  node: TreeNode | null;
  onChapterSaved: () => void;
};

export function Editor({ node, onChapterSaved }: Props) {
  const [text, setText] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (node?.type === 'chapter') {
      setLoading(true);
      setDirty(false);
      projectApi
        .getChapterContent(node.id)
        .then((r) => {
          setText(r.text ?? '');
        })
        .catch(() => setText(''))
        .finally(() => setLoading(false));
    } else {
      setText('');
      setDirty(false);
    }
  }, [node?.id, node?.type, node?.updated_at]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    setDirty(true);
  };

  const handleSave = async () => {
    if (!node || node.type !== 'chapter' || !dirty) return;
    setSaving(true);
    try {
      await projectApi.updateChapterContent(node.id, text);
      setDirty(false);
      onChapterSaved();
    } finally {
      setSaving(false);
    }
  };

  if (!node) {
    return (
      <div className="flex flex-1 items-center justify-center p-10">
        <div className="glass-panel mx-auto max-w-2xl rounded-[32px] px-10 py-12 text-center">
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--muted)]">
            Writing Studio
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">
            Select a chapter to begin writing
          </h2>
          <p className="mt-4 text-base leading-8 text-[var(--muted)]">
            Chapters appear here as a single polished writing surface while the backend keeps
            paragraph structure for precise AI edits.
          </p>
        </div>
      </div>
    );
  }

  if (node.type === 'chapter') {
    return (
      <div className="flex flex-1 flex-col min-w-0">
        <div className="border-b border-[var(--border)] px-8 py-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.26em] text-[var(--muted)]">
                Chapter Editor
              </p>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--ink)]">
                {node.title || 'Chapter'}
              </h2>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-full border border-[var(--border)] bg-[var(--paper-soft)] px-3 py-1.5 text-xs text-[var(--muted)]">
                {dirty ? 'Unsaved changes' : 'Synced'}
              </div>
              <button
                type="button"
                onClick={handleSave}
                disabled={saving || !dirty}
                className="premium-button rounded-2xl px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Save'}
              </button>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-auto px-8 py-8">
          {loading ? (
            <div className="glass-panel rounded-[32px] px-8 py-10 text-[var(--muted)]">
              Loading chapter…
            </div>
          ) : (
            <div className="glass-panel min-h-full rounded-[36px] p-4 md:p-6">
              <textarea
                className="editor-content w-full min-h-[calc(100vh-270px)] resize-none rounded-[28px] bg-transparent px-5 py-4 outline-none placeholder:text-[var(--muted)]"
                placeholder="Write your chapter here. Use blank lines between paragraphs; the system will store them as separate paragraphs in the backend."
                value={text}
                onChange={handleChange}
                spellCheck
              />
            </div>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col min-w-0 overflow-auto p-10">
      <div className="glass-panel max-w-3xl rounded-[32px] p-8">
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--muted)]">
          Document Overview
        </p>
        <h1 className="mb-2 mt-3 text-3xl font-semibold tracking-tight text-[var(--ink)]">
          {node.title || node.type}
        </h1>
        {node.summary && (
          <p className="text-[var(--muted)] leading-8">{node.summary}</p>
        )}
        <p className="mt-5 text-sm text-[var(--muted)]">
          Select a chapter from the tree to edit its content in the central editor.
        </p>
      </div>
    </div>
  );
}
