import React from 'react';
import { Document } from '../types';
import { documentsApi } from '../api/documents';
import { CheckCircle, FileText, Loader2, Plus, Trash2, XCircle } from 'lucide-react';

interface DocumentListProps {
  documents: Document[];
  selectedDocId: string | null;
  onSelectDoc: (id: string | null) => void;
  onOpenUpload: () => void;
  onDeleteDoc: (id: string) => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  selectedDocId,
  onSelectDoc,
  onOpenUpload,
  onDeleteDoc,
}) => {
  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        await documentsApi.delete(id);
        onDeleteDoc(id);
      } catch (err) {
        alert('Failed to delete document.');
      }
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/60 border-r border-slate-800 w-80">
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <h2 className="font-semibold text-sm text-slate-200 uppercase tracking-wider">Knowledge Base</h2>
        <button
          onClick={onOpenUpload}
          className="p-1.5 bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition shadow-md shadow-brand-500/20"
          title="Upload Document"
        >
          <Plus className="h-4 w-4" />
        </button>
      </div>

      <div className="p-3">
        <button
          onClick={() => onSelectDoc(null)}
          className={`w-full text-left px-3 py-2 rounded-xl text-xs font-medium transition flex items-center justify-between ${
            selectedDocId === null
              ? 'bg-brand-600/20 text-brand-300 border border-brand-500/40'
              : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
          }`}
        >
          <span>All Documents (Full Search)</span>
          <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded-full">{documents.length}</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 space-y-1.5 pb-4">
        {documents.length === 0 ? (
          <div className="text-center py-10 px-4">
            <FileText className="h-8 w-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400">No documents ingested yet.</p>
            <p className="text-[11px] text-slate-500 mt-1">Upload a PDF to begin asking questions.</p>
          </div>
        ) : (
          documents.map((doc) => (
            <div
              key={doc.id}
              onClick={() => onSelectDoc(doc.id)}
              className={`group relative p-3 rounded-xl cursor-pointer transition border ${
                selectedDocId === doc.id
                  ? 'bg-slate-800 border-brand-500/50 shadow-sm'
                  : 'bg-slate-950/40 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center space-x-2 min-w-0 pr-6">
                  <FileText className="h-4 w-4 text-brand-400 flex-shrink-0" />
                  <span className="text-xs font-medium text-slate-200 truncate">{doc.title}</span>
                </div>
                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 rounded transition absolute right-2 top-2"
                  title="Delete Document"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>

              <div className="flex items-center space-x-2 mt-2 text-[10px] text-slate-400">
                <span>{doc.total_pages} pages</span>
                <span>•</span>
                <span>{(doc.file_size / 1024).toFixed(0)} KB</span>
                <span className="ml-auto">
                  {doc.status === 'processed' && (
                    <span className="flex items-center text-emerald-400">
                      <CheckCircle className="h-3 w-3 mr-0.5" /> Ready
                    </span>
                  )}
                  {doc.status === 'pending' && (
                    <span className="flex items-center text-amber-400">
                      <Loader2 className="h-3 w-3 mr-0.5 animate-spin" /> Ingesting
                    </span>
                  )}
                  {doc.status === 'failed' && (
                    <span className="flex items-center text-rose-400">
                      <XCircle className="h-3 w-3 mr-0.5" /> Failed
                    </span>
                  )}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
