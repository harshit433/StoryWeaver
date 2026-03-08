import { useState, useEffect, useCallback } from 'react';
import { projectApi } from './api';
import type { TreeNode } from './types';
import { Sidebar } from './components/Sidebar';
import { Editor } from './components/Editor';
import { ChatPanel } from './components/ChatPanel';
import { SettingsDialog } from './components/SettingsDialog';
import { MermaidDiagram } from './components/MermaidDiagram';

export default function App() {
  const [documents, setDocuments] = useState<TreeNode[]>([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null);
  const [loadingTree, setLoadingTree] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);

  const loadDocuments = useCallback(async () => {
    try {
      setError(null);
      const { documents: docs } = await projectApi.listDocuments();
      setDocuments(docs);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load projects');
    }
  }, []);

  const loadTree = useCallback(async (documentId: string) => {
    setLoadingTree(true);
    try {
      setError(null);
      const t = await projectApi.getTree(documentId);
      setTree(t);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load document');
      setTree(null);
    } finally {
      setLoadingTree(false);
    }
  }, []);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  useEffect(() => {
    if (selectedDocumentId) loadTree(selectedDocumentId);
    else setTree(null);
  }, [selectedDocumentId, loadTree]);

  const handleSelectDocument = (id: string) => {
    setSelectedDocumentId(id);
    setSelectedNode(null);
  };

  const handleSelectNode = (node: TreeNode | null) => {
    setSelectedNode(node);
  };

  const refreshTree = useCallback(() => {
    if (selectedDocumentId) loadTree(selectedDocumentId);
  }, [selectedDocumentId, loadTree]);

  // After tree refresh, keep selectedNode in sync (e.g. after AI edit or save)
  useEffect(() => {
    if (!tree || !selectedNode) return;
    const find = (n: TreeNode): TreeNode | null => {
      if (n.id === selectedNode.id) return n;
      for (const c of n.children ?? []) {
        const found = find(c);
        if (found) return found;
      }
      return null;
    };
    const updated = find(tree);
    if (updated) setSelectedNode(updated);
  }, [tree]);

  const handleCreateProject = async () => {
    const title = window.prompt('Project title');
    if (!title?.trim()) return;
    try {
      const { project_id } = await projectApi.createProject(title.trim());
      await loadDocuments();
      setSelectedDocumentId(project_id);
      setSelectedNode(null);
      loadTree(project_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create project');
    }
  };

  const handleCreateChapter = async (documentId: string, title: string) => {
    try {
      await projectApi.createChapter(title, documentId);
      refreshTree();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create chapter');
    }
  };

  const handleDeleteProject = async (documentId: string) => {
    const confirmed = window.confirm('Delete this project and all its chapters? This cannot be undone.');
    if (!confirmed) return;
    try {
      await projectApi.deleteProject(documentId);
      await loadDocuments();
      if (selectedDocumentId === documentId) {
        setSelectedDocumentId(null);
        setSelectedNode(null);
        setTree(null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete project');
    }
  };

  const architectureChart = `
flowchart LR
  User["Writer / Editor"] --> Frontend["Frontend Workspace<br/>React + TypeScript"]
  Frontend --> Api["FastAPI API Layer"]
  Api --> Think["Thinking Agent<br/>Find relevant chapters"]
  Think --> Plan["Planning Agent<br/>Localized edit plan"]
  Plan --> Execute["Execution Engine<br/>Apply operations"]
  Execute --> Graph["Document Graph<br/>Document -> Chapter -> Paragraph"]
  Graph --> Propagation["Summary + Index Propagation"]
  Propagation --> Retrieval["Doc Index + Embeddings"]
  Retrieval --> Think
  Execute --> Frontend
  Graph --> Mongo["MongoDB"]
  Retrieval --> Chroma["Chroma / Semantic Search"]
  Think --> Groq["Groq LLM"]
  Plan --> Groq
`;

  const workflowChart = `
flowchart TD
  Input["User instruction"] --> Read["Read document memory<br/>chapter summaries + structure"]
  Read --> Retrieve["Thinking step<br/>retrieve relevant chapters"]
  Retrieve --> Load["Load numbered chapter view<br/>paragraphs + lines"]
  Load --> Decide["Planning step<br/>choose exact operations"]
  Decide --> Apply["Execute one or more operations"]
  Apply --> Update["Update chapter text / paragraph nodes"]
  Update --> Propagate["Refresh summaries, doc index,<br/>and semantic memory"]
  Propagate --> Sync["Push updated state to UI"]
  Sync --> Done["Writer sees live result"]
`;

  return (
    <div className="min-h-screen text-[var(--ink)]">
      <div className="mx-auto max-w-[1800px] px-4 py-4">
        <div className="flex h-[calc(100vh-2rem)] flex-col">
          <header className="glass-panel-strong mb-4 shrink-0 rounded-[28px] px-6 py-4">
            <div className="flex items-center justify-between gap-6">
              <div className="flex items-center gap-4">
                <div className="glass-panel flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/8 p-2">
                  <img
                    src="/storyweaver-logo.svg"
                    alt="StoryWeaver AI logo"
                    className="h-full w-full object-contain"
                  />
                </div>
                <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[var(--muted)]">
                  Premium Writing Workspace
                </p>
                <h1 className="mt-1 text-2xl font-semibold tracking-tight">StoryWeaver AI</h1>
                </div>
              </div>
              <div className="hidden items-center gap-3 md:flex">
                <button
                  type="button"
                  onClick={() => setSettingsOpen(true)}
                  className="rounded-full border border-[var(--border)] bg-[var(--paper-soft)] px-4 py-2 text-sm text-[var(--muted)] hover:bg-white/10 hover:text-[var(--ink)]"
                >
                  Settings
                </button>
                <div className="rounded-full border border-[var(--border)] bg-[var(--paper-soft)] px-4 py-2 text-sm text-[var(--muted)]">
                  {selectedDocumentId ? 'Document connected' : 'No document selected'}
                </div>
              </div>
            </div>
            {error && (
              <p className="mt-3 rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-600 dark:text-red-300" role="alert">
                {error}
              </p>
            )}
          </header>
          <div className="flex min-h-0 flex-1 gap-4">
            <Sidebar
              documents={documents}
              tree={tree}
              selectedNode={selectedNode}
              onSelectDocument={handleSelectDocument}
              onSelectNode={handleSelectNode}
              onCreateProject={handleCreateProject}
              onCreateChapter={handleCreateChapter}
              onDeleteProject={handleDeleteProject}
              loadingTree={loadingTree}
            />
            <main className="glass-panel-strong flex min-w-0 flex-1 overflow-hidden rounded-[32px]">
              <Editor node={selectedNode} onChapterSaved={refreshTree} />
            </main>
            <ChatPanel documentId={selectedDocumentId} onEditsApplied={refreshTree} />
          </div>
        </div>
        <section className="glass-panel-strong mt-4 rounded-[32px] px-8 py-8">
          <div className="max-w-5xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              About This Project
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              Why I built StoryWeaver AI
            </h2>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              This project began with a story idea that people genuinely loved. I wanted to turn it
              into a novel, but I had no prior experience writing a full book and quickly realized
              that existing tools were not built for the way serious long-form writing actually
              works.
            </p>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              I tried products and AI tools like Reedsy, Scrivener, ChatGPT, Type.io, and others,
              but none of them truly helped. Traditional book-writing tools offered structure without
              intelligence, while general-purpose models struggled to preserve consistency across
              characters, plotlines, environment, and timeline over long stretches of text.
            </p>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              They also failed at precise inline editing. When I wanted one targeted change, the
              model would often rewrite far too much and break the surrounding narrative. That gap is
              exactly why this tool exists.
            </p>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              StoryWeaver AI is my attempt to build a real Cursor for writers: a system that
              understands a book as a structured, evolving whole, keeps continuity intact, and helps
              make specific edits or larger creative changes without losing the story.
            </p>
          </div>
        </section>
        <section className="mt-4 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
          <div className="glass-panel-strong rounded-[32px] px-8 py-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Features
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              What this system is designed to do
            </h2>
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Structured story memory</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  The book is modeled as a structured system instead of a flat document, so the AI
                  can reason over chapters, paragraphs, summaries, and continuity.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Targeted editing</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  Instead of rewriting everything, the engine can plan localized changes such as
                  updating a paragraph, inserting content, or modifying a chapter precisely.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Continuity-aware reasoning</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  Retrieval, summaries, and planning work together so edits stay grounded in plot,
                  timeline, environment, and character consistency across the book.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Writer-first experience</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  The user edits a chapter as a cohesive writing surface, while the backend keeps a
                  more granular representation only for intelligent operations.
                </p>
              </div>
            </div>
          </div>

          <div className="glass-panel-strong rounded-[32px] px-8 py-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Architecture
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              System design at a glance
            </h2>
            <div className="mt-6 space-y-4">
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Interface Layer
                </p>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  A premium frontend for project creation, chapter editing, AI-assisted workflows,
                  and user-owned API key configuration.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Reasoning Layer
                </p>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  Specialized agent steps for thinking, planning, and execution, so the system can
                  understand context before deciding how to change the document.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Knowledge Layer
                </p>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  A doc index, summaries, numbering, and embeddings provide the internal memory
                  required for intelligent retrieval and localized planning.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Persistence Layer
                </p>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  MongoDB stores the structural graph, while vector representations and summaries
                  help the system reason beyond plain keyword lookup.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="glass-panel-strong mt-4 rounded-[32px] px-8 py-8">
          <div className="max-w-6xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Visual Architecture
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              Flowchart view of the system
            </h2>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              These diagrams show how the product is organized as a full intelligent system, not
              just a prompt wrapper. The goal is to make retrieval, planning, execution, and writer
              experience work together as one coherent architecture.
            </p>
            <div className="mt-6 grid gap-4 xl:grid-cols-2">
              <div>
                <h3 className="mb-3 text-lg font-semibold text-[var(--ink)]">System architecture</h3>
                <MermaidDiagram chart={architectureChart} />
              </div>
              <div>
                <h3 className="mb-3 text-lg font-semibold text-[var(--ink)]">Request lifecycle</h3>
                <MermaidDiagram chart={workflowChart} />
              </div>
            </div>
          </div>
        </section>

        <section className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="glass-panel-strong rounded-[32px] px-8 py-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Tech Stack
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              Core technologies used
            </h2>
            <div className="mt-6 grid gap-3">
              {[
                ['Frontend', 'React, TypeScript, Vite, Tailwind CSS'],
                ['Backend', 'FastAPI, Python'],
                ['Primary Database', 'MongoDB for document graph storage'],
                ['Semantic Layer', 'ChromaDB and SentenceTransformers embeddings'],
                ['LLM Access', 'Groq API with user-provided browser-local keys'],
                ['Agent Framework', 'Agno for specialized thinking and planning agents'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] px-5 py-4"
                >
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                    {label}
                  </p>
                  <p className="mt-1 text-sm leading-7 text-[var(--ink)]">{value}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="glass-panel-strong rounded-[32px] px-8 py-8">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              How It Works
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              End-to-end reasoning workflow
            </h2>
            <div className="mt-6 space-y-4">
              {[
                [
                  '1. Understand the document',
                  'The system reads document-level memory, chapter summaries, and structural context so it starts from a whole-book understanding rather than a single prompt.',
                ],
                [
                  '2. Retrieve the right chapters',
                  'A thinking stage identifies the most relevant chapters for the request, using chapter summaries first and full chapter reads when deeper understanding is needed.',
                ],
                [
                  '3. Build a localized plan',
                  'The planning stage converts the user request into precise operations using chapter, paragraph, and line numbering so edits are explainable and actionable.',
                ],
                [
                  '4. Execute and propagate',
                  'The executor applies operations, refreshes summaries, updates indices, and keeps the document state internally consistent after every change.',
                ],
                [
                  '5. Reflect results live in the UI',
                  'The writing surface updates automatically so the user experiences AI editing as part of a real product workflow, not a disconnected chat response.',
                ],
              ].map(([title, body]) => (
                <div
                  key={title}
                  className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5"
                >
                  <h3 className="text-lg font-semibold text-[var(--ink)]">{title}</h3>
                  <p className="mt-2 text-sm leading-7 text-[var(--muted)]">{body}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="glass-panel-strong mt-4 rounded-[32px] px-8 py-8">
          <div className="max-w-5xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Builder Mindset
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              More than coding speed, this project shows systems thinking
            </h2>
            <p className="mt-4 text-base leading-8 text-[var(--muted)]">
              What this project demonstrates is not just the ability to write code quickly, but the
              ability to identify a real product gap, model the problem correctly, and design an
              architecture that can evolve through iteration.
            </p>
            <div className="mt-6 grid gap-4 md:grid-cols-3">
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Problem framing</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  Instead of blaming model quality, the project reframes the challenge as a systems
                  problem involving memory, retrieval, localization, and execution.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Architectural iteration</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  The design evolved through multiple approaches, refining from simple prompting to
                  a more layered workflow with structured retrieval, planning, and execution.
                </p>
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5">
                <h3 className="text-lg font-semibold text-[var(--ink)]">Fast delivery with judgment</h3>
                <p className="mt-2 text-sm leading-7 text-[var(--muted)]">
                  AI tools can accelerate implementation, but the core differentiator is knowing
                  what to build, why it matters, and how to structure it into a reliable product.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="glass-panel-strong mt-4 rounded-[32px] px-8 py-8">
          <div className="max-w-6xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[var(--muted)]">
              Real-World Scenarios
            </p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-[var(--ink)]">
              How this system helps writers in practice
            </h2>
            <p className="mt-4 max-w-4xl text-base leading-8 text-[var(--muted)]">
              The real strength of this system is not just generating text. It is helping a writer
              make meaningful, high-leverage creative decisions while preserving continuity, tone,
              structure, and intent across the whole book.
            </p>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {[
                {
                  title: 'Targeted language upgrades',
                  body:
                    'An author can ask the system to make a chapter more cinematic, tighten pacing in a slow section, heighten tension in a confrontation, or make dialogue sharper without losing the surrounding voice of the book.',
                },
                {
                  title: 'Expand a simple plot into a richer novel',
                  body:
                    'A writer may know the high-level plot but not the deeper narrative texture. The system can help introduce side plots, emotional beats, secondary tensions, recurring motifs, and foreshadowing while keeping the main arc intact.',
                },
                {
                  title: 'Write new chapters in context',
                  body:
                    'Instead of generating disconnected prose, the engine can write whole chapters with awareness of earlier events, existing character dynamics, setting rules, and the narrative direction established by the rest of the manuscript.',
                },
                {
                  title: 'Maintain continuity over long stories',
                  body:
                    'The system helps keep track of who knows what, what happened when, how relationships evolved, and what environmental or timeline constraints already exist, reducing the classic long-form inconsistency problem in general chat models.',
                },
                {
                  title: 'Extend the story intelligently',
                  body:
                    'When the writer wants to continue the plot, the system can suggest credible next developments, deepen stakes, branch subplots, or create stronger cause-and-effect progression because it reasons over the whole document rather than a single passage.',
                },
                {
                  title: 'Inline edits without collateral damage',
                  body:
                    'A writer can ask for very specific changes such as adjusting one reveal, softening one character moment, or adding a callback to an earlier event, without the AI rewriting unrelated parts of the chapter.',
                },
                {
                  title: 'Character-driven rewriting',
                  body:
                    'If a protagonist feels too flat, too passive, or inconsistent, the system can help rewrite scenes so the character voice, emotional reactions, and choices align better across multiple chapters.',
                },
                {
                  title: 'Plot repair and structural fixes',
                  body:
                    'The engine can help identify where a subplot disappears, where pacing collapses, where foreshadowing is missing, or where a later payoff lacks setup, then suggest or apply targeted structural improvements.',
                },
                {
                  title: 'Collaborative creative ideation',
                  body:
                    'Because the system understands the existing story, it can act as a meaningful creative collaborator: proposing twists, alternate scene directions, richer conflicts, and thematic expansions that fit the current manuscript instead of generic suggestions.',
                },
              ].map((item) => (
                <div
                  key={item.title}
                  className="rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-5"
                >
                  <h3 className="text-lg font-semibold text-[var(--ink)]">{item.title}</h3>
                  <p className="mt-2 text-sm leading-7 text-[var(--muted)]">{item.body}</p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-3xl border border-[var(--border)] bg-[var(--paper-soft)] p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                Why these examples matter
              </p>
              <p className="mt-3 max-w-5xl text-base leading-8 text-[var(--muted)]">
                These are strong use cases because they go beyond simple text generation. They show
                how intelligent systems become truly valuable when they combine memory, structure,
                retrieval, planning, and controlled execution. That is what turns AI from a writing
                toy into a serious creative tool.
              </p>
            </div>
          </div>
        </section>
        <SettingsDialog open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      </div>
    </div>
  );
}
