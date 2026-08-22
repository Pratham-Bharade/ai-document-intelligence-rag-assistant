import React, { useEffect, useState } from 'react';
import { adminApi, SystemStats } from '../api/admin';
import { User } from '../types';
import { Activity, Database, FileText, Loader2, MessageSquare, Shield, Users, X } from 'lucide-react';

interface AdminConsoleModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AdminConsoleModal: React.FC<AdminConsoleModalProps> = ({ isOpen, onClose }) => {
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const fetchAdminData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [statsData, usersData] = await Promise.all([
          adminApi.getStats(),
          adminApi.getUsers(),
        ]);
        setStats(statsData);
        setUsers(usersData);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load admin data. Ensure you have Superuser privileges.');
      } finally {
        setLoading(false);
      }
    };

    fetchAdminData();
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-4xl rounded-3xl p-6 shadow-2xl relative max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="h-9 w-9 rounded-xl bg-brand-500/20 border border-brand-500/30 flex items-center justify-center text-brand-300">
              <Shield className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">System Admin Console</h3>
              <p className="text-xs text-slate-400">Database health, metrics, and user management</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto py-5 space-y-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Loader2 className="h-8 w-8 animate-spin text-brand-400 mb-2" />
              <span className="text-xs">Loading database & user statistics...</span>
            </div>
          ) : error ? (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-300 text-xs">
              {error}
            </div>
          ) : (
            <>
              {/* Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-slate-950 border border-slate-800/80 rounded-2xl p-4">
                  <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                    <Users className="h-4 w-4 text-brand-400" />
                    <span>Total Users</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{stats?.total_users ?? 0}</div>
                </div>

                <div className="bg-slate-950 border border-slate-800/80 rounded-2xl p-4">
                  <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                    <FileText className="h-4 w-4 text-indigo-400" />
                    <span>Documents</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{stats?.total_documents ?? 0}</div>
                </div>

                <div className="bg-slate-950 border border-slate-800/80 rounded-2xl p-4">
                  <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                    <Database className="h-4 w-4 text-emerald-400" />
                    <span>Vector Chunks</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{stats?.total_chunks ?? 0}</div>
                </div>

                <div className="bg-slate-950 border border-slate-800/80 rounded-2xl p-4">
                  <div className="flex items-center space-x-2 text-slate-400 text-xs mb-1">
                    <MessageSquare className="h-4 w-4 text-amber-400" />
                    <span>Messages</span>
                  </div>
                  <div className="text-2xl font-bold text-white">{stats?.total_messages ?? 0}</div>
                </div>
              </div>

              {/* User Directory Table */}
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Registered Users Directory ({users.length})
                  </h4>
                  <div className="flex items-center space-x-2 text-xs">
                    <a
                      href="http://127.0.0.1:8000/docs"
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-400 hover:text-brand-300 flex items-center space-x-1"
                    >
                      <span>Interactive API Docs</span>
                    </a>
                    <span className="text-slate-600">·</span>
                    <a
                      href="http://127.0.0.1:8000/metrics"
                      target="_blank"
                      rel="noreferrer"
                      className="text-emerald-400 hover:text-emerald-300 flex items-center space-x-1"
                    >
                      <Activity className="h-3 w-3" />
                      <span>Prometheus</span>
                    </a>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-2 font-medium">User Email</th>
                        <th className="pb-2 font-medium">Role</th>
                        <th className="pb-2 font-medium">Status</th>
                        <th className="pb-2 font-medium">Joined Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/50">
                      {users.map((u) => (
                        <tr key={u.id} className="text-slate-300 hover:bg-slate-900/50">
                          <td className="py-2.5 font-medium text-white">{u.email}</td>
                          <td className="py-2.5">
                            {u.is_superuser ? (
                              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-brand-500/20 text-brand-300 border border-brand-500/30">
                                Superuser / Admin
                              </span>
                            ) : (
                              <span className="px-2 py-0.5 rounded-full text-[10px] bg-slate-800 text-slate-400">
                                Standard User
                              </span>
                            )}
                          </td>
                          <td className="py-2.5">
                            {u.is_active ? (
                              <span className="text-emerald-400 flex items-center space-x-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                                <span>Active</span>
                              </span>
                            ) : (
                              <span className="text-rose-400 flex items-center space-x-1">
                                <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
                                <span>Disabled</span>
                              </span>
                            )}
                          </td>
                          <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                            {new Date(u.created_at).toLocaleDateString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
