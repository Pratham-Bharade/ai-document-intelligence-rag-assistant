import React, { useState } from 'react';
import { SourceCitation } from '../types';
import { BookOpen, ChevronDown, ChevronUp, FileText } from 'lucide-react';

interface SourceCitationPillProps {
  citation: SourceCitation;
  index: number;
}

export const SourceCitationPill: React.FC<SourceCitationPillProps> = ({ citation, index }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="inline-block mr-2 mb-2">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-brand-300 hover:text-brand-200 border border-slate-700 hover:border-brand-500/50 rounded-lg text-xs transition-colors shadow-sm"
      >
        <BookOpen className="h-3.5 w-3.5 text-brand-400" />
        <span>Source {index + 1}</span>
        {citation.page_number && (
          <span className="text-slate-400">· Page {citation.page_number}</span>
        )}
        {citation.score !== undefined && (
          <span className="text-emerald-400 font-mono">({Math.round(citation.score * 100)}%)</span>
        )}
        {isOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
      </button>

      {isOpen && (
        <div className="mt-2 p-3 bg-slate-900 border border-slate-700 rounded-xl text-xs text-slate-300 shadow-xl max-w-lg animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between text-slate-400 mb-1.5 pb-1.5 border-b border-slate-800">
            <span className="flex items-center space-x-1 font-medium text-slate-200">
              <FileText className="h-3.5 w-3.5 text-brand-400 mr-1" />
              Verified Excerpt
            </span>
            {citation.page_number && <span>Page {citation.page_number}</span>}
          </div>
          <p className="whitespace-pre-wrap leading-relaxed text-slate-300 font-mono text-[11px] bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 max-h-40 overflow-y-auto">
            {citation.snippet}
          </p>
        </div>
      )}
    </div>
  );
};
