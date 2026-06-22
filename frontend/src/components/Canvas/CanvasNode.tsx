import { Terminal, FileText, Database, GitBranch, ShieldCheck, BarChart4, ShieldAlert, Palette, Crown, Circle } from 'lucide-react';
import type { CanvasNode } from '../../types/canvas.types';
import { statusConfig } from './canvasNode.styles';

interface Props {
  node: CanvasNode;
  steps: any[];
  isActive: boolean;
  onClick: () => void;
}

const ICONS: Record<string, any> = {
  Supervisor: Crown,
  Dev: Terminal,
  BA: FileText,
  SA: Database,
  DevOps: GitBranch,
  Refinement: ShieldCheck,
  Analytics: BarChart4,
  Critic: ShieldAlert,
  Designer: Palette,
};

export default function CanvasNode({ node, steps, isActive, onClick }: Props) {
  const Icon = ICONS[node.id] || Circle;
  const isSupervisor = node.id === 'Supervisor';
  const config = (statusConfig as any)[node.status] || statusConfig.idle;
  
  const agentSteps = steps.filter((s) => s.agent === node.id || (node.id === 'Supervisor' && s.agent === 'Supervisor'));
  const toolsCount = agentSteps.filter((s) => s.type === 'tool' || s.type === 'command').length;
  const thoughtsCount = agentSteps.filter((s) => s.type === 'thought').length;

  return (
    <div
      onClick={onClick}
      className={`absolute w-[240px] h-[135px] flex flex-col rounded-2xl border backdrop-blur-xl cursor-pointer transition-all duration-300 select-none ${config.border} ${config.bg} ${config.glow} ${
        isActive ? 'ring-2 ring-indigo-500 ring-offset-2 ring-offset-[#0c0c0e] scale-105' : 'hover:scale-[1.03] hover:-translate-y-0.5'
      }`}
      style={{
        left: `${node.x - 120}px`,
        top: `${node.y - 67.5}px`,
        padding: '16px',
      }}
    >
      <div className="flex items-center justify-between mb-2 flex-shrink-0">
        <div className="flex items-center gap-2 min-w-0">
          <div className={`p-1.5 rounded-lg flex items-center justify-center ${config.iconBg}`}>
            <Icon size={14} />
          </div>
          <span className="text-[12px] font-bold text-zinc-150 truncate tracking-wide">
            {node.label}
          </span>
        </div>
        <div className="relative flex h-2 w-2 flex-shrink-0">
          {node.status === 'working' && (
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
          )}
          <span className={`relative inline-flex rounded-full h-2 w-2 ${config.dot}`}></span>
        </div>
      </div>

      <div className="flex items-center mb-2.5 flex-shrink-0">
        <span className={`px-2 py-0.5 text-[9px] font-bold font-mono uppercase rounded-md border ${config.badge}`}>
          {node.status}
        </span>
      </div>

      <div className="w-full border-t border-zinc-800/40 mb-2.5 flex-shrink-0" />

      <div className="flex-1 min-h-0 flex items-stretch">
        <div className="flex-1 min-w-0 flex flex-col justify-center" style={{ paddingRight: '12px', borderRight: '1px solid rgba(63, 63, 70, 0.4)' }}>
          <span className="text-[8px] uppercase tracking-wider text-zinc-500 mb-1 font-semibold block">Activity</span>
          {node.lastStepText ? (
            <div className="text-[9px] font-mono text-zinc-350 bg-zinc-900/45 px-1.5 py-1 rounded border border-zinc-800/30 truncate">
              <span className="text-zinc-650 mr-1">▶</span>
              {node.lastStepText}
            </div>
          ) : (
            <span className="text-[9.5px] text-zinc-550 italic pl-0.5">
              {isSupervisor ? 'Monitoring...' : 'Awaiting task...'}
            </span>
          )}
        </div>

        <div className="w-[88px] flex flex-col justify-center gap-0.5 text-[9px] font-mono text-zinc-450" style={{ paddingLeft: '16px' }}>
          <div className="flex justify-between border-b border-zinc-800/20 pb-0.5">
            <span>Thoughts</span>
            <span className="font-semibold text-zinc-250">{thoughtsCount}</span>
          </div>
          <div className="flex justify-between border-b border-zinc-800/20 pb-0.5">
            <span>Tools</span>
            <span className="font-semibold text-zinc-250">{toolsCount}</span>
          </div>
          <div className="flex justify-between">
            <span>Tokens</span>
            <span className="font-semibold text-zinc-250">{node.tokenUsage || 0}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
