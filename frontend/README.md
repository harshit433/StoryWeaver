# Story Reasoning Engine — Frontend

React + TypeScript + Tailwind frontend for the writing IDE. Create projects, acts, chapters, and paragraphs; edit in the main editor; use the AI panel to apply edits by instruction.

## Run

1. Start the backend (from project root):
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

2. Start the frontend:
   ```bash
   npm install
   npm run dev
   ```

3. Open http://localhost:5173. API requests are proxied to `http://127.0.0.1:8000` via `/api`.

## Features

- **Sidebar**: List projects, expand document tree (acts → chapters → paragraphs). Create project, add act/chapter/paragraph from the tree. Select a node to edit.
- **Editor**: Edit paragraph text and save; summaries update via the backend. For document/act/chapter, view title and summary.
- **AI panel**: Enter instructions (e.g. “Make the storm scene more intense”). The backend retrieves relevant content, reasons, and applies edits; the tree and editor refresh.
