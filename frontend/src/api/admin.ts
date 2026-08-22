import { apiClient } from './client';
import { User } from '../types';

export interface SystemStats {
  total_users: number;
  total_documents: number;
  total_chunks: number;
  total_conversations: number;
  total_messages: number;
}

export const adminApi = {
  getUsers: async (): Promise<User[]> => {
    const res = await apiClient.get<User[]>('/admin/users');
    return res.data;
  },

  getStats: async (): Promise<SystemStats> => {
    const res = await apiClient.get<SystemStats>('/admin/stats');
    return res.data;
  },
};
