import { useState } from 'react';
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
        <div className="text-[13px] text-zinc-500 font-medium select-none py-0.5">
          Working...
        </div>
        <ExecutionTrace steps={steps} isActive={isActive} />
      </div>
    );
  }

  const formatDurationText = (dur?: string): string => {
    if (!dur) return "Worked for a few seconds";
    const num = parseInt(dur);
    if (isNaN(num)) return `Worked for ${dur}`;
    return `Worked for ${num}s`;
  };

  const durationText = formatDurationText(duration);

  return (
    <div className="flex flex-col mb-3 items-start">
      <div
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 py-0.5 w-fit text-[13px] text-zinc-500 font-medium cursor-pointer select-none hover:text-zinc-300 transition-colors"
      >
        <span>{durationText}</span>
        <span className="text-[10px] text-zinc-600 font-sans ml-1 select-none">
          {isOpen ? '▾' : '▸'}
        </span>
      </div>

      {isOpen && (
        <div className="mt-1 pl-2.5 border-l border-zinc-800">
          <ExecutionTrace steps={steps} isActive={false} />
        </div>
      )}
    </div>
  );
}
