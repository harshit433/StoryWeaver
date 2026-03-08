import { useState, useEffect } from 'react';
import type { TreeNode } from '../types';

type Props = {
  documents: TreeNode[];
  tree: TreeNode | null;
  selectedNode: TreeNode | null;
  onSelectDocument: (id: string) => void;
  onSelectNode: (node: TreeNode | null) => void;
  onCreateProject: () => void;
  onCreateChapter: (documentId: string, title: string) => void;
  onDeleteProject: (documentId: string) => void;
  loadingTree: boolean;
};

export function Sidebar({
  documents,
  tree,
  selectedNode,
  onSelectDocument,
  onSelectNode,
  onCreateProject,
  onCreateChapter,
  onDeleteProject,
  loadingTree,
}: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [adding, setAdding] = useState<'chapter' | null>(null);
  const [addParentId, setAddParentId] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    if (tree) setExpanded((prev) => new Set(prev).add(tree.id));
  }, [tree?.id]);

  const toggle = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const startAdd = (kind: 'chapter', parentId: string) => {
    setAdding(kind);
    setAddParentId(parentId);
    setNewTitle('');
  };

  const cancelAdd = () => {
    setAdding(null);
    setAddParentId(null);
    setNewTitle('');
  };

  const submitAdd = () => {
    if (!addParentId || !newTitle.trim()) return;
    if (adding === 'chapter') onCreateChapter(addParentId, newTitle.trim());
    cancelAdd();
  };

  const renderNode = (node: TreeNode, depth: number) => {
    const rawChildren = node.children || [];
    const displayChildren = rawChildren.filter((c) => c.type !== 'paragraph');
    const hasChildren = displayChildren.length > 0;
    const isExpanded = expanded.has(node.id);
    const isSelected = selectedNode?.id === node.id;
    const label = node.title || node.text?.slice(0, 40) || node.type;

    return (
      <div key={node.id} className="select-none">
        <div
          className={`group flex items-center gap-2 rounded-2xl px-3 py-2.5 transition-colors ${
            isSelected
              ? 'bg-[var(--accent-soft)] text-[var(--ink)] soft-ring'
              : 'text-[var(--muted)] hover:bg-white/8 hover:text-[var(--ink)]'
          }`}
          style={{ paddingLeft: `${depth * 14 + 12}px` }}
          onClick={() => onSelectNode(node)}
        >
          {hasChildren && (
            <button
              type="button"
              className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[var(--muted)] hover:bg-white/10 hover:text-[var(--ink)]"
              onClick={(e) => {
                e.stopPropagation();
                toggle(node.id);
              }}
            >
              {isExpanded ? '▼' : '▶'}
            </button>
          )}
          {!hasChildren && <span className="w-6 shrink-0" />}
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--paper-soft)] text-[11px] font-semibold uppercase">
            {node.type === 'document' ? 'D' : 'C'}
          </span>
          <span className="truncate flex-1 text-sm font-medium">{label}</span>
          {node.type === 'document' && (
            <button
              type="button"
              className="subtle-button opacity-0 group-hover:opacity-100 rounded-full px-2.5 py-1 text-[11px] font-medium"
              onClick={(e) => {
                e.stopPropagation();
                startAdd('chapter', node.id);
              }}
            >
              + Chapter
            </button>
          )}
        </div>
        {hasChildren && isExpanded &&
          displayChildren.map((child) => renderNode(child, depth + 1))}
      </div>
    );
  };

  return (
    <aside className="glass-panel-strong flex h-full w-80 flex-col overflow-hidden rounded-[32px]">
      <div className="border-b border-[var(--border)] px-5 py-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Library
            </p>
            <h2 className="mt-1 text-lg font-semibold text-[var(--ink)]">Projects</h2>
          </div>
          <div className="rounded-full border border-[var(--border)] bg-[var(--paper-soft)] px-3 py-1 text-xs text-[var(--muted)]">
            {documents.length}
          </div>
        </div>
        <button
          type="button"
          onClick={onCreateProject}
          className="premium-button mt-4 w-full rounded-2xl px-4 py-3 text-sm font-medium disabled:opacity-50"
        >
          Create New Project
        </button>
      </div>
      <div className="flex-1 overflow-auto px-3 py-4">
        {documents.length === 0 && !loadingTree && (
          <div className="rounded-3xl border border-dashed border-[var(--border)] bg-[var(--paper-soft)] p-5 text-sm text-[var(--muted)]">
            No projects yet. Create one to start building your book workspace.
          </div>
        )}
        {documents.map((doc) => (
          <div key={doc.id} className="mb-3 last:mb-0">
            <div
              className={`group cursor-pointer rounded-3xl px-4 py-3 transition-all ${
                tree?.id === doc.id
                  ? 'bg-[var(--accent-soft)] soft-ring'
                  : 'bg-[var(--paper-soft)] hover:bg-white/10'
              }`}
              onClick={() => onSelectDocument(doc.id)}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--ink)]">{doc.title || doc.id}</p>
                  <p className="mt-0.5 text-xs text-[var(--muted)]">Document workspace</p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="rounded-full border border-[var(--border)] px-2.5 py-1 text-[11px] text-[var(--muted)]">
                    Open
                  </span>
                  <button
                    type="button"
                    className="rounded-full border border-red-400/20 bg-red-500/10 px-2.5 py-1 text-[11px] text-red-600 opacity-0 transition-opacity group-hover:opacity-100 dark:text-red-300"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteProject(doc.id);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
            {tree && tree.id === doc.id && (
              <div className="mt-2 rounded-3xl border border-[var(--border)] bg-[var(--sidebar)]/70 p-2">
                {loadingTree ? (
                  <p className="p-3 text-sm text-[var(--muted)]">Loading your structure…</p>
                ) : (
                  renderNode(tree, 0)
                )}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="border-t border-[var(--border)] bg-[var(--paper-soft)] px-4 py-4">
        {adding && addParentId && (
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--muted)]">
              New {adding}
            </p>
            <input
              type="text"
              className="w-full rounded-2xl border border-[var(--border)] bg-[var(--paper-strong)] px-4 py-3 text-sm outline-none focus:border-[var(--accent)] focus:ring-4 focus:ring-[var(--accent-soft)]"
              placeholder={`${adding} title`}
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submitAdd()}
              autoFocus
            />
            <div className="mt-3 flex gap-2">
              <button
                type="button"
                className="premium-button rounded-2xl px-4 py-2 text-sm font-medium"
                onClick={submitAdd}
              >
                Add
              </button>
              <button
                type="button"
                className="rounded-2xl border border-[var(--border)] px-4 py-2 text-sm text-[var(--muted)] hover:bg-white/8"
                onClick={cancelAdd}
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
