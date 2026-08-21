import React, { useState, useEffect } from 'react';
import { documentsApi } from '../api/documents';
import { Document } from '../types';
import { Navbar } from '../components/Navbar';
import { DocumentList } from '../components/DocumentList';
import { ChatInterface } from '../components/ChatInterface';
import { DocumentUploadModal } from '../components/DocumentUploadModal';

export const DashboardPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState<boolean>(false);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(true);

  const fetchDocs = async () => {
    try {
      const data = await documentsApi.list();
      setDocuments(data);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, []);

  const handleUploadSuccess = (newDoc: Document) => {
    setDocuments((prev) => [newDoc, ...prev]);
    setSelectedDocId(newDoc.id);
  };

  const handleDeleteDoc = (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (selectedDocId === id) {
      setSelectedDocId(null);
    }
  };

  const selectedDoc = documents.find((d) => d.id === selectedDocId);

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 overflow-hidden">
      <Navbar />

      <div className="flex-1 flex overflow-hidden">
        {loadingDocs ? (
          <div className="w-80 border-r border-slate-800 flex items-center justify-center text-slate-500 text-xs">
            Loading knowledge base...
          </div>
        ) : (
          <DocumentList
            documents={documents}
            selectedDocId={selectedDocId}
            onSelectDoc={(id) => setSelectedDocId(id)}
            onOpenUpload={() => setIsUploadOpen(true)}
            onDeleteDoc={handleDeleteDoc}
          />
        )}

        <ChatInterface
          selectedDocId={selectedDocId}
          selectedDocTitle={selectedDoc?.title}
        />
      </div>

      <DocumentUploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onSuccess={handleUploadSuccess}
      />
    </div>
  );
};
