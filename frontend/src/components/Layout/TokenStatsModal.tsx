import { X, Activity } from 'lucide-react';
import { TokenStats } from '../Dashboard/TokenStats';
import type { TokenUsage } from '../../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  tokenUsage: TokenUsage;
}

export default function TokenStatsModal({ isOpen, onClose, tokenUsage }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
      {/* Modal Card */}
      <div 
        className="w-full max-w-3xl rounded-xl border bg-zinc-950 p-6 flex flex-col shadow-2xl animate-fade-in max-h-[85vh] overflow-hidden"
        style={{ borderColor: 'var(--border-color)' }}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-zinc-800 flex-shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded bg-indigo-500/10 text-indigo-400">
              <Activity size={18} />
            </div>
            <div>
              <h2 className="text-base font-bold text-zinc-100">DeepSeek Token Cost Analyzer</h2>
              <p className="text-[11px] text-zinc-400">Real-time cache hit, cache miss, and dollar spend statistics</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/80 rounded-md transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto py-4 pr-1 min-h-0">
          <TokenStats tokenUsage={tokenUsage} />
        </div>
      </div>
    </div>
  );
}
