import { apiClient, API_BASE_URL } from './client';
import { RAGQueryResponse, SourceCitation } from '../types';

export interface StreamCallbacks {
  onSources?: (sources: SourceCitation[]) => void;
  onToken?: (token: string) => void;
  onDone?: () => void;
  onError?: (error: string) => void;
}

export const ragApi = {
  query: async (
    question: string,
    document_id?: string,
    top_k: number = 4,
    mode: string = 'qa',
    hybrid: boolean = false
  ): Promise<RAGQueryResponse> => {
    const res = await apiClient.post<RAGQueryResponse>('/rag/query', {
      question,
      document_id,
      top_k,
      mode,
      hybrid,
    });
    return res.data;
  },

  streamQuery: async (
    question: string,
    callbacks: StreamCallbacks,
    document_id?: string,
    top_k: number = 4,
    mode: string = 'qa',
    hybrid: boolean = false
  ): Promise<void> => {
    const token = localStorage.getItem('token');
    const response = await fetch(`${API_BASE_URL}/rag/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        question,
        document_id,
        top_k,
        mode,
        hybrid,
      }),
    });

    if (!response.ok) {
      throw new Error(`Streaming failed: ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by browser.');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'sources' && callbacks.onSources) {
              callbacks.onSources(data.sources);
            } else if (data.type === 'token' && callbacks.onToken) {
              callbacks.onToken(data.content);
            } else if (data.type === 'done' && callbacks.onDone) {
              callbacks.onDone();
            } else if (data.type === 'error' && callbacks.onError) {
              callbacks.onError(data.error);
            }
          } catch (e) {
            console.error('Failed to parse SSE line:', line);
          }
        }
      }
    }
  },
};
