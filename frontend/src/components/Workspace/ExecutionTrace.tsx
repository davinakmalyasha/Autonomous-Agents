import { groupTraceSteps, type TraceStep } from '../../utils/logParser';
import TraceGroupRow from './TraceGroupRow';

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
