import { useState } from 'react';
import { groupTraceSteps, type TraceStep, type GroupedTraceStep } from '../../utils/logParser';

import { Loader2 } from 'lucide-react';

interface Props {
  steps: TraceStep[];
  isActive?: boolean;
}

export default function ExecutionTrace({ steps, isActive }: Props) {
  const grouped = groupTraceSteps(steps);
  if (grouped.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 py-1 ml-4 pl-1 my-1">
      {grouped.map((group, idx) => (
        <TraceGroupRow 
          key={group.id} 
          group={group} 
          isLastActive={!!isActive && idx === grouped.length - 1} 
        />
      ))}
    </div>
  );
}

function TraceGroupRow({ group, isLastActive }: { group: GroupedTraceStep; isLastActive: boolean }) {
  // Expand agent thoughts and active steps by default
  const [expanded, setExpanded] = useState(group.type === 'thought' || isLastActive);

  // Stable duration generator (matching Google/Antigravity style)
  const getStableDuration = (text: string, type: string): string => {
    let hash = 0;
    for (let i = 0; i < text.length; i++) {
      hash = text.charCodeAt(i) + ((hash << 5) - hash);
    }
    const absHash = Math.abs(hash);
    if (type === 'thought') {
      return ((absHash % 4) + 2) + 's'; // 2s to 5s
    } else if (type === 'command') {
      return ((absHash % 8) + 3) + 's'; // 3s to 10s
    } else {
      return ((absHash % 2) + 1) + 's'; // 1s to 2s
    }
  };

  const getTitle = () => {
    if (isLastActive) {
      if (group.type === 'thought') {
        const agentName = group.agent ? group.agent.toUpperCase() : 'AGENT';
        return `${agentName} — Thinking`;
      }
      if (group.type === 'exploration') return 'Exploring files';
      if (group.type === 'edit') return 'Editing files';
      if (group.type === 'command') return 'Running command';
      return group.title;
    }

    const dur = getStableDuration(JSON.stringify(group.steps), group.type);
    switch (group.type) {
      case 'thought': {
        const agentName = group.agent ? group.agent.toUpperCase() : 'AGENT';
        return `${agentName} — Thought for ${dur}`;
      }
      case 'exploration':
        return group.title; // e.g. "Explored 1 file"
      case 'edit':
        return group.title; // e.g. "Edited 1 file"
      case 'command':
        return `Ran command for ${dur}`;
      default:
        return group.title;
    }
  };

  const hasContent = group.type === 'thought' || group.steps.length > 0;
  const thoughtContent = group.type === 'thought' ? (group.steps[0]?.content || '') : '';

  return (
    <div className="flex flex-col text-[13px] text-zinc-400 mb-1 animate-fade-in">
      {/* Header Row */}
      <div 
        onClick={() => hasContent && setExpanded(!expanded)}
        className="flex items-center gap-1 py-0.5 w-fit cursor-pointer select-none text-zinc-300 font-medium hover:text-zinc-100 transition-colors"
      >
        <span>{getTitle()}</span>
        <span className="text-[10px] text-zinc-500 font-sans ml-1 mr-1">
          {expanded ? '∨' : '〉'}
        </span>
        {isLastActive && <Loader2 size={11} className="text-purple-400 animate-spin" />}
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="mt-0.5 pl-3 flex flex-col gap-1 text-[13px] text-zinc-400 font-sans leading-relaxed">
          {group.type === 'thought' ? (
            <div className="max-w-2xl leading-normal text-zinc-400 font-sans pr-4 whitespace-pre-wrap">
              {thoughtContent}
            </div>
          ) : (
            group.steps.map((s) => {
              // Try to parse JSON args to get clean fields
              let fileName = '';
              let cmdDisplay = '';
              let lineRange = '';
              if (s.args) {
                try {
                  const parsed = JSON.parse(s.args);
                  if (parsed.file_path) {
                    fileName = parsed.file_path.split(/[/\\]/).pop() || '';
                  }
                  if (s.toolName === 'run_command' && parsed.command) {
                    cmdDisplay = parsed.command.length > 80
                      ? parsed.command.substring(0, 80) + '...'
                      : parsed.command;
                  }
                  if (s.toolName === 'search_code' && parsed.pattern) {
                    cmdDisplay = parsed.pattern;
                  }
                  if (s.toolName === 'list_files' && parsed.path) {
                    cmdDisplay = parsed.path.split(/[/\\]/).pop() || parsed.path;
                  }
                  
                  // Extract offset and limit from args as fallback
                  const offset = parsed.offset || 1;
                  const limit = parsed.limit;
                  if (limit) {
                    lineRange = `#L${offset}-${offset + limit - 1}`;
                  } else if (offset > 1) {
                    lineRange = `#L${offset}`;
                  }
                } catch {
                  // Fallback: try simple regex extraction
                  const fileMatch = s.args.match(/"file_path"\s*:\s*"([^"]+)"/);
                  if (fileMatch) fileName = fileMatch[1].split(/[/\\]/).pop() || '';
                  const cmdMatch = s.args.match(/"command"\s*:\s*"([^"]+)"/);
                  if (cmdMatch) cmdDisplay = cmdMatch[1];
                }
              }

              // Extract line range from content if available
              if (s.content && s.toolName === 'read_file') {
                const match = s.content.match(/\(lines (\d+)-(\d+)/);
                if (match) {
                  lineRange = `#L${match[1]}-${match[2]}`;
                }
              }

              const getFileEmoji = (name: string): string => {
                const ext = name.split('.').pop()?.toLowerCase() || '';
                switch (ext) {
                  case 'py': return '🐍';
                  case 'js':
                  case 'jsx': return '🟨';
                  case 'ts':
                  case 'tsx': return '🟦';
                  case 'html': return '🌐';
                  case 'css': return '🎨';
                  case 'json': return '📦';
                  case 'md': return '📝';
                  default: return '📄';
                }
              };

              const emoji = fileName ? getFileEmoji(fileName) : '';
              const emojiPrefix = emoji ? `${emoji} ` : '';

              let desc = '';
              if (s.toolName === 'read_file') {
                desc = `Analyzed ${emojiPrefix}${fileName || 'file'}${lineRange ? ` ${lineRange}` : ''}`;
              } else if (s.toolName === 'write_file') {
                desc = `Wrote ${emojiPrefix}${fileName || 'file'}`;
              } else if (s.toolName === 'edit_file') {
                desc = `Edited ${emojiPrefix}${fileName || 'file'}`;
              } else if (s.toolName === 'run_command') {
                desc = `Ran ${cmdDisplay || 'command'}`;
              } else if (s.toolName === 'search_code') {
                desc = `Searched for ${cmdDisplay || 'pattern'}`;
              } else if (s.toolName === 'list_files') {
                desc = cmdDisplay ? `Listed ${cmdDisplay}` : 'Listed project files';
              } else {
                desc = `${s.toolName || 'tool'}`;
              }

              return (
                <div key={s.id} className="flex flex-col gap-1 mt-0.5">
                  <div className="text-zinc-400 leading-normal font-sans">
                    {desc}
                  </div>
                  {s.content && s.toolName === 'run_command' && (
                    <pre className="mt-1 p-2 bg-zinc-950/40 border border-zinc-900/60 text-zinc-400 rounded overflow-x-auto max-h-48 font-mono text-[11px] leading-relaxed">
                      {s.content}
                    </pre>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}
