import { useState } from 'react';
import { ChevronDown, ChevronRight, Clock } from 'lucide-react';
import ExecutionTrace from './ExecutionTrace';
import type { TraceStep } from '../../utils/logParser';

interface Props {
  steps: TraceStep[];
  isActive?: boolean;
  duration?: string;
}

export default function TraceAccordion({ steps, isActive, duration }: Props) {
  const [isOpen, setIsOpen] = useState(false);

  if (isActive) {
    return (
      <div className="flex flex-col mb-3">
        <ExecutionTrace steps={steps} isActive={isActive} />
      </div>
    );
  }

  // Format duration helper
  const formatDurationText = (dur?: string): string => {
    if (!dur) return "Worked for a few seconds";
    const num = parseInt(dur);
    if (isNaN(num)) return `Worked for ${dur}`;
    if (num < 60) {
      return `Worked for ${num} second${num !== 1 ? 's' : ''}`;
    }
    const mins = Math.floor(num / 60);
    const secs = num % 60;
    if (secs === 0) {
      return `Worked for ${mins} minute${mins !== 1 ? 's' : ''}`;
    }
    return `Worked for ${mins} minute${mins !== 1 ? 's' : ''} ${secs} second${secs !== 1 ? 's' : ''}`;
  };

  const durationText = formatDurationText(duration);

  return (
    <div className="flex flex-col mb-3 align-start">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 py-1 px-2.5 w-fit text-[12px] text-zinc-400 font-medium bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-800/50 rounded-md transition-all select-none hover:text-zinc-200"
      >
        {isOpen ? <ChevronDown size={13} className="text-zinc-500" /> : <ChevronRight size={13} className="text-zinc-500" />}
        <Clock size={12} className="text-zinc-500" />
        <span>{durationText}</span>
      </button>

      {isOpen && (
        <div className="mt-1.5 pl-2.5 border-l border-zinc-900/60">
          <ExecutionTrace steps={steps} isActive={false} />
        </div>
      )}
    </div>
  );
}
