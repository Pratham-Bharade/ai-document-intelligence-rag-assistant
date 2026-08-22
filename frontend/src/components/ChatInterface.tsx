import React, { useState, useRef, useEffect } from 'react';
import { Message } from '../types';
import { ragApi } from '../api/rag';
import { SourceCitationPill } from './SourceCitationPill';
import { Bot, Layers, RotateCcw, Send, Sparkles, User as UserIcon } from 'lucide-react';

interface ChatInterfaceProps {
  selectedDocId: string | null;
  selectedDocTitle?: string;
}

const STORAGE_KEY = 'rag_chat_history_v1';

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
  const [hybrid, setHybrid] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Active key for the current conversation scope
  const activeKey = selectedDocId || 'all_docs';
  const currentMessages = chatHistoryByDoc[activeKey] || [];

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
      <div className="h-14 border-b border-slate-800/80 px-6 flex items-center justify-between bg-slate-900/40">
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-brand-400" />
          <span className="text-xs font-medium text-slate-300">
            Scope: <span className="text-brand-300 font-semibold">{selectedDocTitle || 'All Ingested Knowledge'}</span>
          </span>
        </div>

        <div className="flex items-center space-x-3 text-xs">
          {/* Mode Selector */}
          <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 px-2.5 py-1 rounded-lg">
            <span className="text-slate-500">Mode:</span>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
            >
              <option value="qa">Question Answering</option>
              <option value="summary">Executive Summary</option>
              <option value="extraction">Entity Extraction</option>
              <option value="comparison">Cross Comparison</option>
            </select>
          </div>

          {/* Hybrid search toggle */}
          <button
            onClick={() => setHybrid(!hybrid)}
            className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border transition ${
              hybrid
                ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title="Combine Dense Vectors with BM25 Lexical Keyword Search"
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Hybrid Search</span>
          </button>

          {/* Clear Chat Button for current document */}
          {currentMessages.length > 0 && (
            <button
              onClick={handleClearHistory}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition"
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
            <p className="text-xs text-slate-400 leading-relaxed">
              Ask questions, generate summaries, or compare facts across documents. Every answer cites verified page numbers and text excerpts.
            </p>
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
                className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed shadow-sm ${
                  msg.role === 'user'
                    ? 'bg-brand-600 text-white rounded-tr-none'
                    : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.content}</p>

                {/* Render source citations under assistant message */}
                {msg.role === 'assistant' && msg.sources_json && msg.sources_json.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-800/80">
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
                ? `Ask about ${selectedDocTitle}...`
                : "Ask a question across all documents..."
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
