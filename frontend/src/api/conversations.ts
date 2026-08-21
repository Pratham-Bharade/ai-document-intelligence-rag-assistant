import { apiClient } from './client';
import { Conversation, Message } from '../types';

export const conversationsApi = {
  list: async (): Promise<Conversation[]> => {
    const res = await apiClient.get<Conversation[]>('/conversations');
    return res.data;
  },

  create: async (title?: string): Promise<Conversation> => {
    const res = await apiClient.post<Conversation>('/conversations', { title });
    return res.data;
  },

  get: async (id: string): Promise<Conversation> => {
    const res = await apiClient.get<Conversation>(`/conversations/${id}`);
    return res.data;
  },

  sendMessage: async (conversationId: string, content: string): Promise<Message> => {
    const res = await apiClient.post<Message>(`/conversations/${conversationId}/messages`, { content });
    return res.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/conversations/${id}`);
  },
};
