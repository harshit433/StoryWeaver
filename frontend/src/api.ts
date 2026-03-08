import type { TreeNode, EditPlan } from './types';
import { getStoredGroqApiKey } from './localSettings';

const API_BASE = '/api';

async function request<T>(
  path: string,
  options: RequestInit & { json?: object } = {}
): Promise<T> {
  const { json, ...init } = options;
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(init.headers as Record<string, string>),
  };
  const groqApiKey = getStoredGroqApiKey();
  if (groqApiKey) {
    (headers as Record<string, string>)['X-Groq-Api-Key'] = groqApiKey;
  }
  if (json) {
    (init as RequestInit).body = JSON.stringify(json);
  }
  const res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(
      (err as { error?: string; detail?: string }).error ||
        (err as { error?: string; detail?: string }).detail ||
        res.statusText
    );
  }
  return res.json() as Promise<T>;
}

// Project
export const projectApi = {
  listDocuments: () =>
    request<{ documents: TreeNode[] }>('/project/documents'),

  getTree: (documentId: string) =>
    request<TreeNode>(`/project/tree/${documentId}`),

  createProject: (title: string) =>
    request<{ project_id: string; title: string }>('/project/create', {
      method: 'POST',
      json: { title },
    }),

  deleteProject: (documentId: string) =>
    request<{ status: string; document_id: string }>(`/project/${documentId}`, {
      method: 'DELETE',
    }),

  createChapter: (title: string, documentId: string) =>
    request<{ chapter_id: string; title: string }>('/project/chapter', {
      method: 'POST',
      json: { title, document_id: documentId },
    }),

  createParagraph: (text: string, chapterId: string) =>
    request<{ paragraph_id: string; text: string; summary?: string }>(
      '/project/paragraph',
      {
        method: 'POST',
        json: { text, chapter_id: chapterId },
      }
    ),

  updateParagraph: (paragraphId: string, text: string) =>
    request<{ paragraph_id: string; text: string; summary?: string }>(
      `/project/paragraph/${paragraphId}`,
      {
        method: 'PATCH',
        json: { text },
      }
    ),

  getChapterContent: (chapterId: string) =>
    request<{ chapter_id: string; text: string }>(
      `/project/chapter/${chapterId}/content`
    ),

  updateChapterContent: (chapterId: string, text: string) =>
    request<{ chapter_id: string; text: string }>(
      `/project/chapter/${chapterId}/content`,
      {
        method: 'PATCH',
        json: { text },
      }
    ),
};

// Reasoning (AI) — pass document_id for top-down traversal retrieval
export const reasoningApi = {
  execute: (instruction: string, documentId?: string | null) =>
    request<{
      edit_plan: EditPlan;
      status: string;
      relevant_chapters?: number[];
      reasoning?: string;
      execution_results?: { operation: string; success: boolean }[];
      operations_performed?: number;
    }>('/reasoning/execute', {
      method: 'POST',
      json: { instruction, document_id: documentId ?? undefined },
    }),

  plan: (instruction: string, documentId?: string | null) =>
    request<{ edit_plan: EditPlan }>('/reasoning/plan', {
      method: 'POST',
      json: { instruction, document_id: documentId ?? undefined },
    }),
};
