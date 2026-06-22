import { useState } from 'react';
import { X, Minimize2, Maximize2, MessageSquare } from 'lucide-react';
import type { ChatMessage, AppState, ModelOption } from '../../types';
import PromptDock from './PromptDock';
import MessageStream from './MessageStream';

interface Props {
  messages: ChatMessage[];
  isRunning: boolean;
  workspaceName: string | null;
  chatTitle: string | null;
  selectedModel: string;
  models: ModelOption[];
  state: AppState | null;
  hasActiveChat: boolean;
  notification: string | null;
  onSend: (message: string) => void;
  onCancel: () => void;
  onModelChange: (model: string) => void;
  onClearNotification: () => void;
}

export default function ChatView({
  messages, isRunning,
  selectedModel, models, hasActiveChat, notification,
  onSend, onCancel, onModelChange, onClearNotification,
}: Props) {
  const [minimized, setMinimized] = useState(false);

  return (
    <div 
      className="absolute bottom-6 left-1/2 -translate-x-1/2 z-40 w-full max-w-[850px] flex flex-col pointer-events-auto rounded-2xl border border-zinc-800/80 backdrop-blur-xl shadow-2xl transition-all duration-300"
      style={{
        backgroundColor: 'rgba(18, 18, 20, 0.85)',
        maxHeight: '80vh',
      }}
    >
      {/* Header bar */}
      <div 
        className="flex items-center justify-between border-b border-zinc-800/60 bg-zinc-900/35 flex-shrink-0"
        style={{ paddingLeft: '16px', paddingRight: '16px', paddingTop: '8px', paddingBottom: '8px' }}
      >
        <div className="flex items-center gap-2">
          <MessageSquare size={13} className="text-indigo-400" />
          <span className="text-[11.5px] font-semibold text-zinc-400">
            Supervisor Chat {minimized && `(${messages.length} messages)`}
          </span>
          {isRunning && (
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
          )}
        </div>
        <button
          onClick={() => setMinimized((m) => !m)}
          className="p-1 hover:bg-zinc-850 rounded text-zinc-450 hover:text-zinc-200 transition-colors cursor-pointer flex items-center gap-1.5 text-[10px]"
          title={minimized ? "Expand chat history" : "Collapse chat history"}
        >
          {minimized ? (
            <>
              <Maximize2 size={11} className="text-indigo-400" />
              <span className="text-indigo-400 hover:text-indigo-300 font-semibold">Expand History</span>
            </>
          ) : (
            <>
              <Minimize2 size={11} />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>

      {/* Collapsible Area */}
      <div 
        className="flex-1 flex flex-col overflow-hidden transition-all duration-300 ease-in-out"
        style={{
          maxHeight: minimized ? '0px' : '380px',
          opacity: minimized ? 0 : 1,
        }}
      >
        {/* Notifications */}
        {notification && (
          <div className="flex items-center gap-2.5 mx-4 mt-2 px-3 py-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-[11px] text-blue-300 flex-shrink-0">
            <span className="flex-1 truncate">{notification}</span>
            <button onClick={onClearNotification} className="p-0.5 text-blue-400 hover:text-blue-200">
              <X size={12} />
            </button>
          </div>
        )}

        {/* Message stream */}
        <MessageStream messages={messages} hasActiveChat={hasActiveChat} />
      </div>

      {/* Always visible Bottom Prompt Dock */}
      <div className="border-t border-zinc-800/50 flex-shrink-0">
        <PromptDock onSend={onSend} onCancel={onCancel} isRunning={isRunning} selectedModel={selectedModel} onModelChange={onModelChange} models={models} />
      </div>
    </div>
  );
}
