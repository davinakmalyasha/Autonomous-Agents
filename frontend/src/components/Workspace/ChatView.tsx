import { useRef, useEffect, useState } from 'react';
import { ExternalLink, Maximize2, Minimize2, ChevronRight, Activity, Zap, Info, X } from 'lucide-react';
import type { ChatMessage, AppState, ModelOption, ChatData } from '../../types';
import MessageBubble from './MessageBubble';
import PromptDock from './PromptDock';

interface Props {
  messages: ChatMessage[];
  isRunning: boolean;
  workspaceName: string | null;
  chatTitle: string | null;
  selectedModel: string;
  models: ModelOption[];
  state: AppState | null;
  hasActiveChat: boolean;
  activeChat: ChatData | null;
  notification: string | null;
  onSend: (message: string) => void;
  onCancel: () => void;
  onModelChange: (model: string) => void;
  onClearNotification: () => void;
  onOpenStats?: () => void;
}

export default function ChatView({
  messages, isRunning, workspaceName, chatTitle,
  selectedModel, models, state, hasActiveChat, activeChat, notification,
  onSend, onCancel, onModelChange, onClearNotification, onOpenStats,
}: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);
  const lastScrollHeightRef = useRef(0);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Initialize lastScrollHeightRef on mount
  useEffect(() => {
    if (scrollRef.current) {
      lastScrollHeightRef.current = scrollRef.current.scrollHeight;
    }
  }, []);

  // ── Auto-scroll to bottom when new messages arrive ──
  useEffect(() => {
    if (!scrollRef.current || !isAtBottomRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // ── Auto-scroll to bottom when inner content size changes ──
  useEffect(() => {
    if (!contentRef.current) return;
    const observer = new ResizeObserver(() => {
      if (isAtBottomRef.current && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
    observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, [messages, hasActiveChat]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    
    const wasAtBottom = isAtBottomRef.current;
    const heightChanged = el.scrollHeight !== lastScrollHeightRef.current;
    
    let bottom = el.scrollHeight - el.clientHeight <= el.scrollTop + 60;
    
    // Protect isAtBottom state during size transitions
    if (heightChanged && wasAtBottom) {
      bottom = true;
    }
    
    lastScrollHeightRef.current = el.scrollHeight;
    isAtBottomRef.current = bottom;
  };

  // ── Breadcrumb ──
  const breadcrumb = workspaceName && chatTitle
    ? `${workspaceName} / ${chatTitle}`
    : workspaceName
      ? `${workspaceName} / Select a conversation`
      : 'Add a project folder to get started';

  const agentNode = state?.active_node;

  // Combine stored chat token usage and current running usage (if pipeline is active)
  const totalInput = (activeChat?.token_usage?.total_input_tokens || 0) + (isRunning ? (state?.token_usage?.total_input_tokens || 0) : 0);
  const totalOutput = (activeChat?.token_usage?.total_output_tokens || 0) + (isRunning ? (state?.token_usage?.total_output_tokens || 0) : 0);
  const totalCost = (activeChat?.token_usage?.total_cost || 0) + (isRunning ? (state?.token_usage?.total_cost || 0) : 0);
  
  const showPill = hasActiveChat;

  return (
    <div className="flex flex-col flex-1 min-w-0 h-full bg-zinc-950">
      {/* ═══════ Top bar with breadcrumb + actions ═══════ */}
      <div className="flex items-center justify-between flex-shrink-0 h-9 px-4 border-b border-zinc-800">
        {/* Breadcrumb — truncated with ellipsis */}
        <div className="flex items-center gap-1.5 text-[12px] text-zinc-400 truncate min-w-0 flex-1 mr-4">
          <ChevronRight size={11} className="text-zinc-600 flex-shrink-0" />
          <span className="truncate">{breadcrumb}</span>
          {agentNode && (
            <span className="flex items-center gap-1 ml-2 px-1.5 py-0.5 text-[10px] bg-purple-500/10 text-purple-400 rounded font-semibold flex-shrink-0 animate-pulse-slow">
              <Activity size={9} /> {agentNode.toUpperCase()}
            </span>
          )}
        </div>

        {/* Right-aligned actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {showPill && (
            <button
              onClick={onOpenStats}
              title="Click to view detailed DeepSeek cost & cache efficiency analysis"
              className="flex items-center gap-2.5 px-2.5 py-1 text-[11px] bg-zinc-900 border border-zinc-800 rounded-md text-zinc-400 flex-shrink-0 cursor-pointer hover:bg-zinc-800/80 hover:border-zinc-700 hover:text-zinc-200 transition-all"
            >
              <div className="flex items-center gap-1">
                <span className="text-zinc-500 font-medium">Burned:</span>
                <span className="text-yellow-500 font-mono font-semibold">
                  {(totalInput + totalOutput).toLocaleString()}
                </span>
              </div>
              <div className="h-2.5 w-[1px] bg-zinc-800" />
              <div className="flex items-center gap-1">
                <span className="text-zinc-500 font-medium">Context:</span>
                <span className="text-blue-400 font-mono font-semibold">
                  {((totalInput / 1000000) * 100).toFixed(4)}%
                </span>
                <span className="text-zinc-600 text-[10px]">
                  ({totalInput.toLocaleString()}/1M)
                </span>
              </div>
              <div className="h-2.5 w-[1px] bg-zinc-800" />
              <div className="flex items-center gap-1">
                <span className="text-zinc-500 font-medium">Cost:</span>
                <span className="text-emerald-500 font-mono font-semibold">
                  ${totalCost.toFixed(5)}
                </span>
              </div>
            </button>
          )}
          {/* TEST API — bypasses all logic */}
          <button
            onClick={() => { console.log('[TEST] Calling testApi...'); (window as any).testApi?.(); }}
            className="flex items-center gap-1 px-2 py-0.5 text-[10px] font-bold text-yellow-400 bg-yellow-500/10 hover:bg-yellow-500/20 border border-yellow-500/30 rounded transition-colors"
          >
            TEST API
          </button>
          {/* Open IDE button */}
          <button className="flex items-center gap-1.5 px-2.5 py-1 text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-md transition-colors">
            <ExternalLink size={11} className="text-blue-400" />
            <span>Open IDE</span>
          </button>
          {/* Full-screen toggle */}
          <button
            onClick={() => setIsFullscreen((v) => !v)}
            className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
            title={isFullscreen ? 'Exit fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 size={12} /> : <Maximize2 size={12} />}
          </button>
        </div>
      </div>

      {/* ═══════ Inline notification banner ═══════ */}
      {notification && (
        <div className="flex items-center gap-2.5 mx-4 mt-2 px-4 py-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[12px] text-blue-300">
          <Info size={14} className="text-blue-400 flex-shrink-0" />
          <span className="flex-1">{notification}</span>
          <button
            onClick={onClearNotification}
            className="p-0.5 text-blue-400 hover:text-blue-200 hover:bg-blue-500/20 rounded transition-colors flex-shrink-0"
          >
            <X size={13} />
          </button>
        </div>
      )}

      {/* ═══════ Message stream ═══════ */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-6 py-4"
      >
        {/* ── Empty / landing state ── */}
        {!hasActiveChat && messages.length <= 1 ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-center max-w-md px-4">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-zinc-900 border border-zinc-800 mb-6">
                <Zap size={28} className="text-yellow-400" />
              </div>
              <h2 className="text-xl font-bold text-zinc-200 mb-3">Antigravity v3</h2>
              <p className="text-[14px] text-zinc-400 leading-relaxed mb-6">
                Multi-Agent AI Workspace — Supervisor + Developer agent with file & code tools.
              </p>
              <div className="flex flex-col gap-2.5 text-left mx-auto max-w-xs">
                <div className="flex items-center gap-2.5 text-[12px] text-zinc-500">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-[10px] font-bold flex-shrink-0">1</span>
                  Add a project folder from the sidebar
                </div>
                <div className="flex items-center gap-2.5 text-[12px] text-zinc-500">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-[10px] font-bold flex-shrink-0">2</span>
                  Click <strong className="text-zinc-400">+ New Conversation</strong> inside that project
                </div>
                <div className="flex items-center gap-2.5 text-[12px] text-zinc-500">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-[10px] font-bold flex-shrink-0">3</span>
                  Start typing — the Developer agent uses tools to read, write, and run code
                </div>
              </div>
            </div>
          </div>
        ) : (
          /* ── Message list ── */
          <div ref={contentRef} className="max-w-3xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
          </div>
        )}
      </div>

      {/* ═══════ Bottom prompt dock ═══════ */}
      <PromptDock
        onSend={onSend}
        onCancel={onCancel}
        isRunning={isRunning}
        selectedModel={selectedModel}
        onModelChange={onModelChange}
        models={models}
      />
    </div>
  );
}
