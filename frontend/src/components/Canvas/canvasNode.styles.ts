export const statusConfig = {
  idle: {
    border: 'border-zinc-800/70 hover:border-zinc-700/80',
    bg: 'bg-[#141416]/80',
    dot: 'bg-zinc-650',
    iconBg: 'bg-zinc-900/60 text-zinc-400 border border-zinc-800/40',
    glow: 'shadow-[0_4px_24px_rgba(0,0,0,0.45)]',
    badge: 'bg-zinc-900/65 text-zinc-450 border-zinc-800/60',
  },
  working: {
    border: 'border-indigo-500/50 hover:border-indigo-400',
    bg: 'bg-gradient-to-br from-zinc-950/95 to-indigo-950/15',
    dot: 'bg-indigo-500 shadow-[0_0_8px_#6366f1]',
    iconBg: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/25',
    glow: 'shadow-[0_0_20px_rgba(99,102,241,0.12)]',
    badge: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/25 animate-pulse',
  },
  completed: {
    border: 'border-emerald-500/40 hover:border-emerald-400',
    bg: 'bg-gradient-to-br from-zinc-950/95 to-emerald-950/10',
    dot: 'bg-emerald-500 shadow-[0_0_6px_#10b981]',
    iconBg: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
    glow: 'shadow-[0_4px_24px_rgba(0,0,0,0.45)]',
    badge: 'bg-emerald-500/10 text-emerald-450 border-emerald-500/20',
  },
  failed: {
    border: 'border-red-500/40 hover:border-red-400',
    bg: 'bg-gradient-to-br from-zinc-950/95 to-red-950/15',
    dot: 'bg-red-500 shadow-[0_0_8px_#ef4444]',
    iconBg: 'bg-red-500/10 text-red-400 border border-red-500/25',
    glow: 'shadow-[0_0_20px_rgba(239,68,68,0.12)]',
    badge: 'bg-red-500/10 text-red-450 border-red-500/25',
  },
};
