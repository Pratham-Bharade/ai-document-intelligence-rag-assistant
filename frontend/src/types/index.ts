export interface User {
  id: string;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  page_number: number;
  text: string;
  metadata_json?: Record<string, any>;
}

export interface Document {
  id: string;
  user_id: string;
  title: string;
  filename: string;
  file_size: number;
  mime_type: string;
  total_pages: number;
  status: 'pending' | 'processed' | 'failed';
  created_at: string;
  updated_at: string;
  chunks?: DocumentChunk[];
}

export interface SourceCitation {
  page_number?: number;
  document_id?: string;
  score?: number;
  snippet: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources_json?: SourceCitation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface RAGQueryResponse {
  answer: string;
  provider?: string;
  model?: string;
  sources: SourceCitation[];
  total_sources: number;
  mode: string;
  guardrails?: {
    faithfulness_score?: number;
    is_grounded?: boolean;
    status?: string;
    blocked?: boolean;
  };
}
