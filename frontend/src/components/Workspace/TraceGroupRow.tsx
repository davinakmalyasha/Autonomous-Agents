import { useState } from 'react';
import type { GroupedTraceStep } from '../../utils/logParser';
import TraceStepRow from './TraceStepRow';

interface Props {
  group: GroupedTraceStep;
  isLastActive: boolean;
}

export default function TraceGroupRow({ group, isLastActive }: Props) {
  const [expanded, setExpanded] = useState(group.type === 'thought' || isLastActive);

  // Stable duration generator (matching Google/Antigravity style)
  const getStableDuration = (text: string, type: string): string => {
    let hash = 0;
    for (let i = 0; i < text.length; i++) hash = text.charCodeAt(i) + ((hash << 5) - hash);
    const absHash = Math.abs(hash);
    return type === 'thought' ? ((absHash % 4) + 2) + 's' : ((absHash % 8) + 3) + 's';
  };

  const getTitle = () => {
    if (isLastActive) {
      if (group.type === 'thought') return 'Thinking...';
      if (group.type === 'exploration') return 'Exploring files...';
      if (group.type === 'edit') return 'Editing files...';
      return group.title;
    }
    const dur = getStableDuration(JSON.stringify(group.steps), group.type);
    if (group.type === 'thought') return `Thought for ${dur}`;
    if (group.type === 'exploration' || group.type === 'edit') {
      const stepCount = group.steps.length;
      const searchCount = group.steps.filter(s => s.toolName === 'search_code').length;
      if (group.type === 'exploration' && searchCount > 0) {
        return `Explored ${stepCount - searchCount} file${(stepCount - searchCount) !== 1 ? 's' : ''}, ${searchCount} search${searchCount !== 1 ? 'es' : ''}`;
      }
      return group.title;
    }
    return group.title;
  };

  const hasCollapsibleContent = group.type === 'thought' || group.type === 'exploration' || group.type === 'edit';

  if (!hasCollapsibleContent) {
    return (
      <div className="pl-0 flex flex-col gap-1 text-[13px] text-zinc-400 font-sans leading-relaxed">
        {group.steps.map((s) => (
          <TraceStepRow key={s.id} step={s} />
        ))}
      </div>
    );
  }

  const thoughtContent = group.steps[0]?.content || '';
  const lines = thoughtContent.split('\n').map(l => l.trim()).filter(Boolean);
  const thoughtTitle = lines[0] || 'Thinking';
  const thoughtBody = lines.slice(1).join('\n');

  return (
    <div className="flex flex-col text-[13px] text-zinc-400 mb-1 animate-fade-in">
      {/* Header Row */}
      <div 
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 py-0.5 w-fit cursor-pointer select-none text-zinc-500 font-medium hover:text-zinc-300 transition-colors"
      >
        <span>{getTitle()}</span>
        <span className="text-[10px] text-zinc-600 font-sans ml-1 select-none">
          {expanded ? '▾' : '▸'}
        </span>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="mt-0.5 pl-3 ml-1.5 border-l border-zinc-800/50 flex flex-col gap-1 text-[13.5px] leading-relaxed">
          {group.type === 'thought' ? (
            <div className="max-w-2xl leading-relaxed text-zinc-400 font-sans pr-4 py-0.5">
              <div className="font-semibold text-zinc-200 mb-0.5">{thoughtTitle}</div>
              {thoughtBody && <div className="text-[12.5px] text-zinc-400 font-normal whitespace-pre-wrap">{thoughtBody}</div>}
            </div>
          ) : (
            group.steps.map((s) => (
              <TraceStepRow key={s.id} step={s} />
            ))
          )}
        </div>
      )}
    </div>
  );
}
