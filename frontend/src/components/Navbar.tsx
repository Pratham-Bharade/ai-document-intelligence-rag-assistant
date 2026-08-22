import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { AdminConsoleModal } from './AdminConsoleModal';
import { Bot, LogOut, Shield, User as UserIcon } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const [isAdminOpen, setIsAdminOpen] = useState(false);

  return (
    <>
      <header className="h-16 border-b border-slate-800 bg-slate-900/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-brand-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-white tracking-tight">AI Document Intelligence</h1>
            <p className="text-xs text-slate-400">Enterprise RAG Assistant</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          {user && (
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2 text-sm text-slate-300 bg-slate-800/80 px-3 py-1.5 rounded-full border border-slate-700">
                <UserIcon className="h-4 w-4 text-brand-400" />
                <span>{user.full_name || user.email}</span>
                {user.is_superuser && (
                  <button
                    onClick={() => setIsAdminOpen(true)}
                    className="flex items-center text-xs bg-brand-500/20 hover:bg-brand-500/30 text-brand-300 px-2.5 py-0.5 rounded-full border border-brand-500/40 transition cursor-pointer"
                    title="Open Admin Console"
                  >
                    <Shield className="h-3 w-3 mr-1 text-brand-400" /> Admin Console
                  </button>
                )}
              </div>

              <button
                onClick={logout}
                className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
                title="Log Out"
              >
                <LogOut className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Admin Management Modal */}
      {user?.is_superuser && (
        <AdminConsoleModal
          isOpen={isAdminOpen}
          onClose={() => setIsAdminOpen(false)}
        />
      )}
    </>
  );
};
