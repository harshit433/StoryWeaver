export type NodeType = 'document' | 'chapter' | 'paragraph' | 'event';

export interface TreeNode {
  id: string;
  type: NodeType;
  title?: string;
  text?: string;
  summary?: string;
  parent_id?: string;
  children_ids: string[];
  children?: TreeNode[];
  created_at?: string;
  updated_at?: string;
}

export interface EditOperation {
  operation: string;
  number?: number;
  chapter_number?: number;
  paragraph_number?: number;
  line_number?: number;
  before_paragraph_number?: number | null;
  after_line_number?: number | null;
}

export interface EditPlan {
  relevant_chapters: number[];
  reasoning: string;
  operations: EditOperation[];
}
