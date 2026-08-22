import React, { useState } from 'react';
import { SourceCitation } from '../types';
import { CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';

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
        className={`inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl text-xs font-medium transition shadow-sm border ${
          isOpen
            ? 'bg-brand-600/20 text-brand-200 border-brand-500/50'
            : 'bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-white border-slate-800 hover:border-slate-700'
        }`}
      >
        <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        <span className="font-semibold text-brand-300">
          {citation.page_number ? `Page ${citation.page_number}` : `Source ${index + 1}`}
        </span>
        <span className="text-slate-500">|</span>
        <span className="text-[11px] text-slate-400">Click to verify</span>
        {isOpen ? <ChevronUp className="h-3 w-3 text-slate-400" /> : <ChevronDown className="h-3 w-3 text-slate-400" />}
      </button>

      {isOpen && (
        <div className="mt-2.5 p-3.5 bg-slate-950 border border-brand-500/30 rounded-2xl text-xs text-slate-200 shadow-2xl max-w-xl animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between text-slate-400 mb-2 pb-2 border-b border-slate-800">
            <span className="flex items-center space-x-1.5 font-semibold text-brand-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Verified Document Grounding Excerpt</span>
            </span>
            {citation.page_number && (
              <span className="px-2 py-0.5 rounded-md bg-brand-500/10 text-brand-300 font-bold border border-brand-500/20 text-[11px]">
                Exact Page: {citation.page_number}
              </span>
            )}
          </div>
          <p className="whitespace-pre-wrap leading-relaxed text-slate-300 font-sans text-xs bg-slate-900/90 p-3 rounded-xl border border-slate-800 max-h-48 overflow-y-auto">
            {citation.snippet}
          </p>
        </div>
      )}
    </div>
  );
};
