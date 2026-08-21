import React, { useState, useRef } from 'react';
import { documentsApi } from '../api/documents';
import { Document } from '../types';
import { CheckCircle2, FileUp, Loader2, UploadCloud, X } from 'lucide-react';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (doc: Document) => void;
}

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({ isOpen, onClose, onSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState<string>('');
  const [uploading, setUploading] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      if (selected.type === 'application/pdf' || selected.name.endsWith('.pdf')) {
        setFile(selected);
        if (!title) setTitle(selected.name.replace(/\.[^/.]+$/, ''));
        setError(null);
      } else {
        setError('Only PDF documents are supported.');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.type === 'application/pdf' || selected.name.endsWith('.pdf')) {
        setFile(selected);
        if (!title) setTitle(selected.name.replace(/\.[^/.]+$/, ''));
        setError(null);
      } else {
        setError('Only PDF documents are supported.');
      }
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError('Please select a PDF file.');
      return;
    }

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const doc = await documentsApi.upload(file, title || undefined, (pct) => {
        setProgress(pct);
      });
      onSuccess(doc);
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload and process document.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <FileUp className="h-5 w-5 text-brand-400" />
            <h3 className="font-semibold text-white">Upload Knowledge Document</h3>
          </div>
          <button
            onClick={onClose}
            disabled={uploading}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleUpload} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs">
              {error}
            </div>
          )}

          {/* Drag and drop box */}
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
              isDragOver
                ? 'border-brand-400 bg-brand-500/10'
                : file
                ? 'border-emerald-500/50 bg-emerald-500/5'
                : 'border-slate-700 hover:border-slate-600 bg-slate-950/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className="hidden"
            />
            {file ? (
              <div className="flex flex-col items-center space-y-2 text-emerald-400">
                <CheckCircle2 className="h-10 w-10 text-emerald-400" />
                <span className="font-medium text-sm text-slate-200">{file.name}</span>
                <span className="text-xs text-slate-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
              </div>
            ) : (
              <div className="flex flex-col items-center space-y-2 text-slate-400">
                <UploadCloud className="h-10 w-10 text-brand-400 animate-pulse" />
                <span className="text-sm font-medium text-slate-200">Drag & drop your PDF here</span>
                <span className="text-xs text-slate-500">or click to browse files (max 50MB)</span>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">Document Title (Optional)</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Employee Benefits Handbook 2026"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-slate-200 focus:outline-none focus:border-brand-500 transition"
            />
          </div>

          {uploading && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-slate-400">
                <span>Ingesting and Vectorizing Document...</span>
                <span>{progress}%</span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                  className="bg-brand-500 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end space-x-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={uploading}
              className="px-4 py-2 text-sm text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!file || uploading}
              className="px-5 py-2 text-sm font-medium bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-xl flex items-center space-x-2 transition shadow-lg shadow-brand-600/20"
            >
              {uploading && <Loader2 className="h-4 w-4 animate-spin" />}
              <span>{uploading ? 'Processing...' : 'Upload & Ingest'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
