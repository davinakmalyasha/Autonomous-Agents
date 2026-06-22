import { Copy, ThumbsUp, ThumbsDown, Share2, AlertTriangle, Wrench, Terminal, FileText, Search } from 'lucide-react';
import type { ChatMessage } from '../../types';
import TraceAccordion from './TraceAccordion';

interface Props {
  message: ChatMessage;
}

/** Pick an icon for tool calls based on the tool name */
function toolIcon(content: string) {
  if (content.includes('[read_file]')) return <FileText size={12} className="text-blue-400" />;
  if (content.includes('[write_file]')) return <FileText size={12} className="text-green-400" />;
  if (content.includes('[edit_file]')) return <FileText size={12} className="text-yellow-400" />;
  if (content.includes('[run_command]')) return <Terminal size={12} className="text-cyan-400" />;
  if (content.includes('[search_code]')) return <Search size={12} className="text-pink-400" />;
  if (content.includes('[list_files]')) return <FileText size={12} className="text-zinc-400" />;
  return <Wrench size={12} className="text-purple-400" />;
}

/** Check if a message content is a tool call */
function isToolCall(content: string): boolean {
  return content.startsWith('🔧 [');
}

export default function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isError = message.role === 'error';
  const isAgent = message.role === 'agent';
  const isSystem = message.role === 'system';
  const isTool = isAgent && isToolCall(message.content);

  return (
    <div className="animate-fade-in group" style={{ marginBottom: '24px' }}>
      {/* ────────────────────────────────────
          USER MESSAGE — simple text display
          ──────────────────────────────────── */}
      {isUser && (
        <div className="flex justify-end">
          <div 
            className="max-w-[80%] text-[14px] text-zinc-100 leading-relaxed bg-zinc-800 border border-zinc-700/50"
            style={{ padding: '10px 16px', borderRadius: '14px' }}
          >
            {message.content}
          </div>
        </div>
      )}

      {/* ────────────────────────────────────
          TOOL CALL — special rendering with icon
          ──────────────────────────────────── */}
      {isTool && (
        <div 
          className="flex items-start gap-2 rounded-lg bg-indigo-500/5 border border-indigo-500/15"
          style={{ padding: '12px' }}
        >
          <div className="flex-shrink-0 mt-0.5">
            {toolIcon(message.content)}
          </div>
          <div className="min-w-0">
            <span className="text-zinc-500 font-semibold text-[10px] uppercase tracking-wider">
              {message.agentName || 'Developer'}
            </span>
            <div className="text-zinc-300 font-mono text-[11px] mt-0.5 leading-relaxed whitespace-pre-wrap break-all">
              {message.content}
            </div>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────
          AGENT MESSAGE — with status + actions
          ──────────────────────────────────── */}
      {isAgent && !isTool && (
        <div>
          {/* Agent name label */}
          {message.agentName && (
            <div className="text-[10px] font-semibold text-zinc-500 uppercase tracking-wider mb-1.5">
              {message.agentName}
            </div>
          )}
          
          {/* Nested Collapsible Trace Accordion */}
          {!!message.metadata?.isTrace && Array.isArray(message.metadata.steps) && 
           (message.duration === 'active' || message.metadata.steps.length > 0) && (
            <TraceAccordion 
              steps={message.metadata.steps as any} 
              isActive={message.duration === 'active'}
              duration={message.metadata?.duration as string || message.duration}
            />
          )}

          {/* Main response text content */}
          {message.content && message.content !== '(Execution Trace)' && (
            <div className="text-[14px] text-zinc-200 leading-relaxed whitespace-pre-wrap">
              {message.content}
            </div>
          )}



          {/* Inline action icons — right-aligned, revealed on hover */}
          <div className="flex items-center justify-end gap-0.5 mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-md transition-colors"
              title="Export / Share"
            >
              <Share2 size={13} />
            </button>
            <button
              className="p-1.5 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 rounded-md transition-colors"
              title="Copy to clipboard"
              onClick={() => navigator.clipboard?.writeText(message.content)}
            >
              <Copy size={13} />
            </button>
            <button
              className="p-1.5 text-zinc-500 hover:text-green-400 hover:bg-zinc-800 rounded-md transition-colors"
              title="Thumbs up"
            >
              <ThumbsUp size={13} />
            </button>
            <button
              className="p-1.5 text-zinc-500 hover:text-red-400 hover:bg-zinc-800 rounded-md transition-colors"
              title="Thumbs down"
            >
              <ThumbsDown size={13} />
            </button>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────
          ERROR MESSAGE — alert/error block
          ──────────────────────────────────── */}
      {isError && (
        <div 
          className="flex items-start gap-2.5 rounded-lg bg-red-500/5 border border-red-500/15"
          style={{ padding: '12px' }}
        >
          <AlertTriangle size={14} className="text-red-400 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-[13px] font-semibold text-red-400">Error</span>
            <p className="text-[13px] text-red-300/80 mt-0.5 leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          </div>
        </div>
      )}

      {/* ────────────────────────────────────
          SYSTEM MESSAGE — low-contrast italic
          ──────────────────────────────────── */}
      {isSystem && (
        <div className="flex items-center gap-2 text-[12px] text-zinc-500 italic px-1">
          <div className="w-1 h-1 rounded-full bg-zinc-600 flex-shrink-0" />
          {message.content}
        </div>
      )}
    </div>
  );
}
