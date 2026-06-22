import type { TraceStep } from '../../utils/logParser';

interface Props {
  step: TraceStep;
}

export default function TraceStepRow({ step }: Props) {
  let fileName = '', cmdDisplay = '', lineRange = '';

  if (step.args) {
    try {
      const parsed = JSON.parse(step.args);
      if (parsed.file_path) fileName = parsed.file_path.split(/[/\\]/).pop() || '';
      if (step.toolName === 'run_command' && parsed.command) {
        cmdDisplay = parsed.command.length > 60 ? parsed.command.substring(0, 60) + '...' : parsed.command;
      }
      if (step.toolName === 'search_code' && parsed.pattern) cmdDisplay = parsed.pattern;
      if (step.toolName === 'list_files' && parsed.path) cmdDisplay = parsed.path.split(/[/\\]/).pop() || parsed.path;
      
      const offset = parsed.offset || 1, limit = parsed.limit;
      if (limit) lineRange = `#L${offset}-${offset + limit - 1}`;
      else if (offset > 1) lineRange = `#L${offset}`;
    } catch {
      const fileMatch = step.args.match(/"file_path"\s*:\s*"([^"]+)"/);
      if (fileMatch) fileName = fileMatch[1].split(/[/\\]/).pop() || '';
      const cmdMatch = step.args.match(/"command"\s*:\s*"([^"]+)"/);
      if (cmdMatch) cmdDisplay = cmdMatch[1];
    }
  }

  if (step.content && step.toolName === 'read_file') {
    const match = step.content.match(/\(lines (\d+)-(\d+)/);
    if (match) lineRange = `#L${match[1]}-${match[2]}`;
  }

  if (step.toolName === 'read_file') {
    return (
      <div className="flex items-center gap-1.5 py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <span>Analyzed</span>
        <span className="text-orange-500 font-bold text-[12px] select-none">&lt;/&gt;</span>
        <span className="text-zinc-200 font-mono font-medium">{fileName || 'file'}</span>
        {lineRange && <span className="text-zinc-600 font-mono text-[11px]">{lineRange}</span>}
      </div>
    );
  }

  if (step.toolName === 'write_file' || step.toolName === 'edit_file') {
    const isEdit = step.toolName === 'edit_file';
    return (
      <div className="flex items-center gap-1.5 py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <span>{isEdit ? 'Edited' : 'Wrote'}</span>
        <span className={isEdit ? "text-yellow-500 font-bold text-[12px] select-none" : "text-green-500 font-bold text-[12px] select-none"}>&lt;/&gt;</span>
        <span className="text-zinc-200 font-mono font-medium">{fileName || 'file'}</span>
      </div>
    );
  }

  if (step.toolName === 'search_code') {
    return (
      <div className="flex items-center gap-1.5 py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <span>Searched</span>
        <span className="text-zinc-300 font-mono font-medium bg-zinc-900 px-1 py-0.2 rounded border border-zinc-800/60">{cmdDisplay || 'pattern'}</span>
      </div>
    );
  }

  if (step.toolName === 'run_command') {
    return (
      <div className="flex flex-col py-0.5 text-zinc-400 font-sans text-[12.5px]">
        <div className="flex items-center gap-1.5">
          <span>Ran command</span>
          <span className="text-zinc-300 font-mono font-medium bg-zinc-900 px-1 py-0.2 rounded border border-zinc-800/60 truncate max-w-sm">{cmdDisplay}</span>
        </div>
        {step.content && (
          <pre className="mt-1 p-2 bg-zinc-950/50 border border-zinc-900 text-zinc-500 rounded overflow-x-auto max-h-32 font-mono text-[10.5px] leading-normal max-w-xl">
            {step.content}
          </pre>
        )}
      </div>
    );
  }

  if (step.toolName === 'list_files') {
    return (
      <div className="flex items-center gap-1.5 py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <span>Listed files in</span>
        <span className="text-zinc-200 font-mono font-medium">{cmdDisplay || 'folder'}</span>
      </div>
    );
  }

  if (step.toolName === 'task' || step.toolName === 'start_async_task') {
    let name = 'Subagent';
    let taskDesc = '';
    if (step.args) {
      try {
        const parsed = JSON.parse(step.args);
        name = parsed.name || 'Subagent';
        taskDesc = parsed.task || '';
      } catch {}
    }
    const isAsync = step.toolName === 'start_async_task';
    return (
      <div className="flex flex-col py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <div className="flex items-center gap-1.5">
          <span className="text-zinc-500 font-semibold">{isAsync ? 'Spawning async' : 'Delegating to'}</span>
          <span className="px-1.5 py-0.5 rounded text-[11px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{name} subagent</span>
        </div>
        {taskDesc && (
          <div className="mt-1 pl-2 ml-1 border-l border-zinc-800 text-[11.5px] text-zinc-500 font-normal line-clamp-2 hover:line-clamp-none transition-all cursor-pointer whitespace-pre-wrap max-w-xl">
            {taskDesc}
          </div>
        )}
      </div>
    );
  }

  if (step.toolName === 'task' || step.toolName === 'start_async_task') {
    let name = 'Subagent';
    let taskDesc = '';
    if (step.args) {
      try {
        const parsed = JSON.parse(step.args);
        name = parsed.name || 'Subagent';
        taskDesc = parsed.task || '';
      } catch {}
    }
    const isAsync = step.toolName === 'start_async_task';
    return (
      <div className="flex flex-col py-0.5 text-zinc-400 font-sans text-[12.5px] leading-relaxed">
        <div className="flex items-center gap-1.5">
          <span className="text-zinc-500 font-semibold">{isAsync ? 'Spawning async' : 'Delegating to'}</span>
          <span className="px-1.5 py-0.5 rounded text-[11px] font-bold bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">{name} subagent</span>
        </div>
        {taskDesc && (
          <div className="mt-1 pl-2 ml-1 border-l border-zinc-800 text-[11.5px] text-zinc-500 font-normal line-clamp-2 hover:line-clamp-none transition-all cursor-pointer whitespace-pre-wrap max-w-xl">
            {taskDesc}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="py-0.5 text-zinc-400 font-sans text-[12.5px]">
      {step.title || step.toolName || 'Tool Call'}
    </div>
  );
}
