import { apiClient } from './client';
import { User } from '../types';

export const authApi = {
  register: async (email: string, password: string, full_name?: string): Promise<User> => {
    const res = await apiClient.post<User>('/auth/register', { email, password, full_name });
    return res.data;
  },

  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    const res = await apiClient.post('/auth/login/json', { email, password });
    return res.data;
  },

  getMe: async (): Promise<User> => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  resetPassword: async (email: string, password: string): Promise<{ message: string }> => {
    const res = await apiClient.post<{ message: string }>('/auth/reset-password', { email, password });
    return res.data;
  },
};
