import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Message } from '../types';
import { ragApi } from '../api/rag';
import { SourceCitationPill } from './SourceCitationPill';
import { Bot, Check, ChevronDown, Layers, RotateCcw, Send, Sparkles, User as UserIcon } from 'lucide-react';

interface ChatInterfaceProps {
  selectedDocId: string | null;
  selectedDocTitle?: string;
}

const STORAGE_KEY = 'rag_chat_history_v1';

const MODE_OPTIONS = [
  {
    id: 'qa',
    name: 'Question Answering',
    badge: 'Factual & Grounded',
    desc: 'Direct, synthesized answers with verified page citations and strict anti-hallucination grounding.',
    icon: '💬',
  },
  {
    id: 'summary',
    name: 'Executive Summary',
    badge: 'Leadership Brief',
    desc: '3-tier structured brief: Executive Overview, Key Policies, and Deadlines & Numerical Requirements.',
    icon: '📑',
  },
  {
    id: 'extraction',
    name: 'Entity Extraction',
    badge: 'Structured Data',
    desc: 'Extracts figures, dates, monetary amounts, and clauses into clean, machine-readable JSON format.',
    icon: '📊',
  },
  {
    id: 'comparison',
    name: 'Cross Comparison',
    badge: 'Multi-Doc Matrix',
    desc: 'Side-by-side comparative analysis, change tracking, and contradiction detection across documents.',
    icon: '⚖️',
  },
];

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ selectedDocId, selectedDocTitle }) => {
  // Store persistent conversation histories partitioned by document id
  const [chatHistoryByDoc, setChatHistoryByDoc] = useState<Record<string, Message[]>>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [mode, setMode] = useState<string>('qa');
  const [isModeDropdownOpen, setIsModeDropdownOpen] = useState<boolean>(false);
  const [hybrid, setHybrid] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const modeDropdownRef = useRef<HTMLDivElement>(null);

  // Active key for the current conversation scope
  const activeKey = selectedDocId || 'all_docs';
  const currentMessages = chatHistoryByDoc[activeKey] || [];
  const currentModeInfo = MODE_OPTIONS.find((m) => m.id === mode) || MODE_OPTIONS[0];

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modeDropdownRef.current && !modeDropdownRef.current.contains(event.target as Node)) {
        setIsModeDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Persist histories to localStorage whenever they update
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(chatHistoryByDoc));
    } catch (err) {
      console.warn('Failed to persist chat history:', err);
    }
  }, [chatHistoryByDoc]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentMessages, loading, selectedDocId]);

  const handleClearHistory = () => {
    setChatHistoryByDoc((prev) => ({
      ...prev,
      [activeKey]: [],
    }));
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userQuestion = input.trim();
    setInput('');

    // Create user message
    const userMsg: Message = {
      id: Date.now().toString(),
      conversation_id: activeKey,
      role: 'user',
      content: userQuestion,
      created_at: new Date().toISOString(),
    };

    // Prepare placeholder assistant message for streaming tokens
    const assistantMsgId = (Date.now() + 1).toString();
    const initialAssistantMsg: Message = {
      id: assistantMsgId,
      conversation_id: activeKey,
      role: 'assistant',
      content: '',
      sources_json: [],
      created_at: new Date().toISOString(),
    };

    setChatHistoryByDoc((prev) => ({
      ...prev,
      [activeKey]: [...(prev[activeKey] || []), userMsg, initialAssistantMsg],
    }));

    setLoading(true);
    let accumulatedContent = '';

    try {
      await ragApi.streamQuery(
        userQuestion,
        {
          onSources: (incomingSources) => {
            setChatHistoryByDoc((prev) => ({
              ...prev,
              [activeKey]: (prev[activeKey] || []).map((msg) =>
                msg.id === assistantMsgId ? { ...msg, sources_json: incomingSources } : msg
              ),
            }));
          },
          onToken: (token) => {
            accumulatedContent += token;
            setChatHistoryByDoc((prev) => ({
              ...prev,
              [activeKey]: (prev[activeKey] || []).map((msg) =>
                msg.id === assistantMsgId ? { ...msg, content: accumulatedContent } : msg
              ),
            }));
          },
          onDone: () => {
            setLoading(false);
          },
          onError: (err) => {
            setChatHistoryByDoc((prev) => ({
              ...prev,
              [activeKey]: (prev[activeKey] || []).map((msg) =>
                msg.id === assistantMsgId
                  ? { ...msg, content: `Error: ${err}` }
                  : msg
              ),
            }));
            setLoading(false);
          },
        },
        selectedDocId || undefined,
        4,
        mode,
        hybrid
      );
    } catch (err: any) {
      setChatHistoryByDoc((prev) => ({
        ...prev,
        [activeKey]: (prev[activeKey] || []).map((msg) =>
          msg.id === assistantMsgId
            ? { ...msg, content: `Failed to stream answer: ${err.message}` }
            : msg
        ),
      }));
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950">
      {/* Header bar with Mode & Hybrid settings */}
      <div className="h-16 border-b border-slate-800/80 px-6 flex items-center justify-between bg-slate-900/40 relative z-30">
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-brand-400" />
          <span className="text-xs font-medium text-slate-300">
            Scope: <span className="text-brand-300 font-semibold">{selectedDocTitle || 'All Ingested Knowledge'}</span>
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          {/* Custom Mode Selector with Detailed Descriptions */}
          <div className="relative" ref={modeDropdownRef}>
            <button
              onClick={() => setIsModeDropdownOpen(!isModeDropdownOpen)}
              className="flex items-center space-x-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 px-3 py-1.5 rounded-xl text-slate-200 transition shadow-sm"
              title="Change reasoning and formatting mode"
            >
              <span>{currentModeInfo.icon}</span>
              <span className="font-medium">{currentModeInfo.name}</span>
              <ChevronDown className={`h-3.5 w-3.5 text-slate-400 transition-transform ${isModeDropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown Menu with Definitions */}
            {isModeDropdownOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-2 animate-in fade-in zoom-in-95 duration-150 z-50 divide-y divide-slate-800/50">
                <div className="px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Select AI Reasoning Mode
                </div>
                <div className="py-1 space-y-1">
                  {MODE_OPTIONS.map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => {
                        setMode(opt.id);
                        setIsModeDropdownOpen(false);
                      }}
                      className={`w-full text-left p-2.5 rounded-xl transition flex items-start space-x-3 ${
                        mode === opt.id
                          ? 'bg-brand-500/15 border border-brand-500/30 text-white'
                          : 'hover:bg-slate-800/60 text-slate-300'
                      }`}
                    >
                      <span className="text-lg leading-none mt-0.5">{opt.icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-xs text-slate-100">{opt.name}</span>
                          {mode === opt.id && <Check className="h-3.5 w-3.5 text-brand-400" />}
                        </div>
                        <p className="text-[11px] text-slate-400 leading-tight mt-1">
                          {opt.desc}
                        </p>
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Hybrid search toggle */}
          <button
            onClick={() => setHybrid(!hybrid)}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border transition ${
              hybrid
                ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Combine Dense Semantic Vectors with Sparse BM25 Keyword Search (RRF)"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Hybrid Search</span>
          </button>

          {/* Clear Chat Button for current document */}
          {currentMessages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition"
              title="Clear conversation for this document"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {currentMessages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto">
            <div className="h-12 w-12 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400 mb-4 shadow-lg shadow-brand-500/5">
              <Bot className="h-6 w-6" />
            </div>
            <h3 className="text-base font-semibold text-slate-200 mb-1">
              {selectedDocTitle ? `Researching ${selectedDocTitle}` : 'How can I assist your document research?'}
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed mb-3">
              Ask questions, generate executive summaries, or extract structured data. Every answer cites verified page numbers and text excerpts.
            </p>
            <div className="inline-flex items-center space-x-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-full text-[11px] text-slate-400">
              <span>Active Mode:</span>
              <span className="font-semibold text-brand-300">{currentModeInfo.name}</span>
              <span>·</span>
              <span>{currentModeInfo.badge}</span>
            </div>
          </div>
        ) : (
          currentMessages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start space-x-3 ${
                msg.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {msg.role === 'assistant' && (
                <div className="h-8 w-8 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white flex-shrink-0 shadow-md">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div
                className={`max-w-3xl rounded-2xl p-5 leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-none text-sm'
                    : 'bg-slate-900 border border-slate-800 text-slate-100 rounded-tl-none text-sm'
                }`}
              >
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="markdown-content">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ node, ...props }) => (
                          <h1 className="text-xl font-extrabold text-slate-100 mt-4 mb-2 pb-1 border-b border-slate-800" {...props} />
                        ),
                        h2: ({ node, ...props }) => (
                          <h2 className="text-lg font-bold text-brand-300 mt-3 mb-2" {...props} />
                        ),
                        h3: ({ node, ...props }) => (
                          <h3 className="text-base font-semibold text-slate-200 mt-2 mb-1" {...props} />
                        ),
                        p: ({ node, ...props }) => (
                          <p className="text-sm text-slate-200 leading-relaxed mb-2.5 last:mb-0" {...props} />
                        ),
                        ul: ({ node, ...props }) => (
                          <ul className="list-disc list-outside ml-4 space-y-1.5 my-2.5 text-sm text-slate-200" {...props} />
                        ),
                        ol: ({ node, ...props }) => (
                          <ol className="list-decimal list-outside ml-4 space-y-1.5 my-2.5 text-sm text-slate-200" {...props} />
                        ),
                        li: ({ node, ...props }) => (
                          <li className="leading-relaxed pl-1" {...props} />
                        ),
                        strong: ({ node, ...props }) => (
                          <strong className="font-bold text-brand-300" {...props} />
                        ),
                        em: ({ node, ...props }) => (
                          <em className="italic text-slate-300" {...props} />
                        ),
                        blockquote: ({ node, ...props }) => (
                          <blockquote className="border-l-4 border-brand-500/70 pl-3 py-1 my-2.5 text-slate-300 italic bg-brand-500/5 rounded-r" {...props} />
                        ),
                        code: ({ node, className, children, ...props }) => (
                          <code className="bg-slate-950 px-1.5 py-0.5 rounded text-brand-300 text-xs font-mono border border-slate-800" {...props}>
                            {children}
                          </code>
                        ),
                        table: ({ node, ...props }) => (
                          <div className="overflow-x-auto my-3 rounded-lg border border-slate-800">
                            <table className="min-w-full text-xs text-left" {...props} />
                          </div>
                        ),
                        th: ({ node, ...props }) => (
                          <th className="bg-slate-800/90 px-3 py-2 font-semibold text-slate-200 border-b border-slate-700" {...props} />
                        ),
                        td: ({ node, ...props }) => (
                          <td className="px-3 py-2 border-b border-slate-800/60 text-slate-300" {...props} />
                        ),
                        hr: ({ node, ...props }) => (
                          <hr className="my-3.5 border-slate-800" {...props} />
                        ),
                      }}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}

                {/* Render source citations under assistant message */}
                {msg.role === 'assistant' && msg.sources_json && msg.sources_json.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80">
                    <span className="text-[11px] font-medium text-slate-400 block mb-1.5">
                      Grounding Sources ({msg.sources_json.length}):
                    </span>
                    <div className="flex flex-wrap">
                      {msg.sources_json.map((src, i) => (
                        <SourceCitationPill key={i} citation={src} index={i} />
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {msg.role === 'user' && (
                <div className="h-8 w-8 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center text-brand-300 flex-shrink-0">
                  <UserIcon className="h-4 w-4" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/30">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto flex items-center space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              selectedDocTitle
                ? `Ask about ${selectedDocTitle} in ${currentModeInfo.name} mode...`
                : `Ask across all documents in ${currentModeInfo.name} mode...`
            }
            disabled={loading}
            className="flex-1 bg-slate-900 border border-slate-800 focus:border-brand-500 rounded-xl px-4 py-3 text-sm text-slate-200 focus:outline-none transition shadow-inner"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="px-4 py-3 bg-brand-600 hover:bg-brand-500 disabled:opacity-40 text-white rounded-xl flex items-center justify-center transition shadow-lg shadow-brand-500/20"
          >
            <Send className="h-4 w-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
