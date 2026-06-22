import { useState, useRef, useEffect } from 'react';
import { Plus, Mic, ChevronDown, GitBranch, Send, Square } from 'lucide-react';
import type { ModelOption } from '../../types';

interface Props {
  onSend: (message: string) => void;
  onCancel?: () => void;
  isRunning: boolean;
  selectedModel: string;
  onModelChange: (model: string) => void;
  models: ModelOption[];
}

interface SlashCommand {
  command: string;
  description: string;
  example: string;
  hasArgs: boolean;
}

const SLASH_COMMANDS: SlashCommand[] = [
  {
    command: '/plan',
    description: 'Analyze deeply and create an implementation plan in planning.md',
    example: '/plan build a calculator web app',
    hasArgs: true
  },
  {
    command: '/help',
    description: 'Show available systems, specialist agents, and workflows',
    example: '/help',
    hasArgs: false
  },
  {
    command: '/start',
    description: 'Reset or initialize workspace department resources',
    example: '/start',
    hasArgs: false
  },
  {
    command: '/session-reset',
    description: 'Clear the active agent session and log history',
    example: '/session-reset',
    hasArgs: false
  }
];

export default function PromptDock({
  onSend,
  onCancel,
  isRunning,
  selectedModel,
  onModelChange,
  models,
}: Props) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [showModelPicker, setShowModelPicker] = useState(false);

  // Autocomplete States
  const [activeCommandIndex, setActiveCommandIndex] = useState(0);
  const [showCommands, setShowCommands] = useState(false);
  const [filteredCommands, setFilteredCommands] = useState<SlashCommand[]>([]);

  // Sync scroll between textarea and overlay
  const handleScroll = () => {
    if (textareaRef.current && overlayRef.current) {
      overlayRef.current.scrollTop = textareaRef.current.scrollTop;
      overlayRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  };

  // ── Auto-resize textarea ──
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    handleScroll();
  }, [value]);

  const checkAutocomplete = () => {
    const el = textareaRef.current;
    if (!el) return;
    
    const caretPos = el.selectionStart || 0;
    const beforeCursor = value.slice(0, caretPos);
    
    // Match word starting with / at cursor position
    const match = beforeCursor.match(/\/(\w*)$/);
    if (match) {
      const typed = match[1].toLowerCase();
      const filtered = SLASH_COMMANDS.filter(cmd => 
        cmd.command.toLowerCase().substring(1).startsWith(typed)
      );
      setFilteredCommands(filtered);
      setShowCommands(filtered.length > 0);
      setActiveCommandIndex(0);
    } else {
      setShowCommands(false);
      setFilteredCommands([]);
    }
  };

  // Run autocomplete check on value change
  useEffect(() => {
    checkAutocomplete();
  }, [value]);

  const selectCommand = (cmd: SlashCommand) => {
    const el = textareaRef.current;
    if (!el) return;
    
    const caretPos = el.selectionStart || 0;
    const beforeCursor = value.slice(0, caretPos);
    const lastSlashIndex = beforeCursor.lastIndexOf('/');
    
    if (lastSlashIndex !== -1) {
      const start = value.slice(0, lastSlashIndex);
      const end = value.slice(caretPos);
      const replacement = cmd.command + (cmd.hasArgs ? ' ' : '');
      const newValue = start + replacement + end;
      setValue(newValue);
      
      // Reset cursor position to right after the inserted command
      setTimeout(() => {
        if (textareaRef.current) {
          const newCaretPos = lastSlashIndex + replacement.length;
          textareaRef.current.selectionStart = newCaretPos;
          textareaRef.current.selectionEnd = newCaretPos;
          textareaRef.current.focus();
        }
      }, 0);
    }
    setShowCommands(false);
  };

  const handleSend = () => {
    const trimmed = value.trim();
    console.log('[PromptDock] handleSend called, value=%o trimmed=%o isRunning=%o', value, trimmed, isRunning);
    if (!trimmed) return;
    console.log('[PromptDock] calling onSend with:', trimmed);
    onSend(trimmed);
    setValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showCommands) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setActiveCommandIndex((prev) => (prev + 1) % filteredCommands.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setActiveCommandIndex((prev) => (prev - 1 + filteredCommands.length) % filteredCommands.length);
        return;
      }
      if (e.key === 'Enter') {
        e.preventDefault();
        selectCommand(filteredCommands[activeCommandIndex]);
        return;
      }
      if (e.key === 'Escape') {
        e.preventDefault();
        setShowCommands(false);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Syntax highlighting for commands in the textarea input
  const highlightText = (text: string) => {
    if (!text) return null;
    const words = text.split(/(\s+)/);
    return words.map((word, idx) => {
      const cmd = SLASH_COMMANDS.find(c => c.command === word);
      if (cmd) {
        return (
          <span key={idx} className="bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded-md font-mono font-semibold">
            {word}
          </span>
        );
      }
      return word;
    });
  };

  // ── Find display name for selected model ──
  const selectedModelName = models.find((m) => m.id === selectedModel)?.name ?? 'Claude Opus 4.6 (Thinking)';

  return (
    <div className="w-full flex-shrink-0" style={{ paddingLeft: '16px', paddingRight: '16px', paddingTop: '10px', paddingBottom: '12px' }}>
      {/* Pill-shaped dock — centered, full width */}
      <div
        className="prompt-dock relative flex flex-col w-full bg-zinc-900 border border-zinc-850/80 rounded-xl transition-shadow"
        style={{ padding: '12px 16px' }}
      >
        {/* ── Autocomplete dropdown ── */}
        {showCommands && (
          <>
            <div
              className="fixed inset-0 z-40 cursor-default"
              onClick={() => setShowCommands(false)}
            />
            <div className="absolute bottom-full left-0 right-0 mb-2.5 bg-zinc-900/95 backdrop-blur-md border border-zinc-800 rounded-xl shadow-2xl overflow-hidden z-50 flex flex-col max-h-60">
              <div className="px-3 py-1.5 border-b border-zinc-800 text-[11px] text-zinc-500 font-semibold uppercase tracking-wider">
                Available Actions
              </div>
              <div className="overflow-y-auto py-1">
                {filteredCommands.map((cmd, idx) => (
                  <button
                    key={cmd.command}
                    onClick={() => selectCommand(cmd)}
                    className={`flex flex-col w-full px-3.5 py-2 text-left transition-colors border-l-2 ${
                      idx === activeCommandIndex
                        ? 'bg-blue-500/10 border-blue-500 text-zinc-100'
                        : 'border-transparent text-zinc-300 hover:bg-zinc-800/50 hover:text-zinc-200'
                    }`}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="text-[14px] font-mono font-semibold text-blue-400">{cmd.command}</span>
                      <span className="text-[11px] text-zinc-500 font-mono">{cmd.example}</span>
                    </div>
                    <span className="text-[12px] text-zinc-400 mt-0.5">{cmd.description}</span>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ── Text input area ── */}
        <div className="relative w-full" style={{ minHeight: 38, maxHeight: 200 }}>
          {/* Highlight Overlay */}
          <div
            ref={overlayRef}
            className="absolute inset-0 pointer-events-none text-[14px] leading-relaxed text-zinc-100 whitespace-pre-wrap break-words overflow-hidden"
            style={{ 
              fontFamily: 'inherit',
              paddingTop: '8px',
              paddingBottom: '8px',
              paddingLeft: '12px',
              paddingRight: '12px'
            }}
          >
            {highlightText(value)}
            {!value && <span className="text-zinc-500">Ask anything, @ to mention, / for actions</span>}
          </div>
          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            onKeyUp={checkAutocomplete}
            onSelect={checkAutocomplete}
            onClick={checkAutocomplete}
            onScroll={handleScroll}
            placeholder=""
            rows={1}
            className="w-full bg-transparent border-none outline-none resize-none text-[14px] text-transparent caret-zinc-100 leading-relaxed relative z-10"
            style={{ 
              minHeight: 38, 
              maxHeight: 200,
              paddingTop: '8px',
              paddingBottom: '8px',
              paddingLeft: '12px',
              paddingRight: '12px'
            }}
          />
        </div>

        {/* ── Bottom toolbar ── */}
        <div 
          className="flex items-center justify-between border-t border-zinc-800"
          style={{ marginTop: '10px', paddingTop: '10px' }}
        >
          {/* Left side: Plus, Worktree, Model selector */}
          <div className="flex items-center gap-1">
            {/* Plus / Attach */}
            <button
              className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
              title="Add attachment"
            >
              <Plus size={16} />
            </button>

            {/* Worktree */}
            <button
              className="flex items-center gap-1 px-2 py-1 text-[12px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
              title="Worktree"
            >
              <GitBranch size={13} />
              <span>Worktree</span>
            </button>

            {/* Model selector dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowModelPicker((v) => !v)}
                className="flex items-center gap-1 px-2 py-1 text-[12px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
              >
                <span className="truncate max-w-[160px]">{selectedModelName}</span>
                <ChevronDown size={10} className="text-zinc-500 flex-shrink-0" />
              </button>

              {showModelPicker && (
                <>
                  {/* Backdrop */}
                  <div
                    className="fixed inset-0 z-40"
                    onClick={() => setShowModelPicker(false)}
                  />
                  {/* Dropdown */}
                  <div className="absolute bottom-full left-0 mb-1 z-50 w-64 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden">
                    <div className="py-1 max-h-64 overflow-y-auto">
                      {models.map((m) => (
                        <button
                          key={m.id}
                          onClick={() => { onModelChange(m.id); setShowModelPicker(false); }}
                          className={`flex items-center gap-2 w-full px-3 py-2 text-[13px] text-left transition-colors ${
                            m.id === selectedModel
                              ? 'bg-blue-500/10 text-blue-400'
                              : 'text-zinc-300 hover:bg-zinc-800'
                          }`}
                        >
                          <span className="truncate">{m.name}</span>
                          {m.provider && (
                            <span className="text-[10px] text-zinc-600 flex-shrink-0 ml-auto">{m.provider}</span>
                          )}
                        </button>
                      ))}
                      {models.length === 0 && (
                        <div className="px-3 py-2 text-[12px] text-zinc-600 italic">No models available</div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Right side: Microphone */}
          <button
            className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors"
            title="Voice input"
          >
            <Mic size={16} />
          </button>

          {/* Send/Stop button */}
          {(() => {
            const showStop = isRunning && !value.trim();
            const handleButtonClick = () => {
              if (showStop) {
                console.log('[PromptDock] Stop button clicked, calling onCancel...');
                onCancel?.();
              } else {
                handleSend();
              }
            };

            return (
              <button
                onClick={handleButtonClick}
                disabled={!showStop && !value.trim()}
                className={`p-1.5 rounded-lg transition-colors ${
                  showStop
                    ? 'text-red-500 hover:text-red-400 hover:bg-red-500/10'
                    : value.trim()
                      ? 'text-blue-400 hover:text-blue-300 hover:bg-blue-500/10'
                      : 'text-zinc-600 cursor-not-allowed'
                }`}
                title={showStop ? 'Stop execution' : 'Send message'}
              >
                {showStop ? <Square size={16} className="fill-current" /> : <Send size={16} />}
              </button>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
