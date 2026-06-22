import { Settings, ExternalLink } from 'lucide-react';

interface Props {
  workspaceName: string | null;
  chatTitle: string | null;
  onOpenSettings: () => void;
  onOpenStats: () => void;
  totalInput: number;
  totalOutput: number;
  totalCost: number;
  showPill: boolean;
}

export default function TitleBar({
  workspaceName,
  chatTitle,
  onOpenSettings,
  onOpenStats,
  totalInput,
  totalOutput,
  totalCost,
  showPill,
}: Props) {
  const breadcrumb = workspaceName && chatTitle
    ? `${workspaceName} / ${chatTitle}`
    : workspaceName
      ? `${workspaceName} / Select a conversation`
      : 'VinCode Workspace';

  return (
    <header className="relative flex items-center justify-between select-none flex-shrink-0 h-[38px] bg-[#0c0c0e] border-b border-zinc-800/60 px-3 z-50" style={{ WebkitAppRegion: 'drag' } as any}>
      {/* Left: App Identity */}
      <div className="flex items-center gap-2" style={{ WebkitAppRegion: 'no-drag', paddingLeft: '16px' } as any}>
        <span className="text-[12px] font-bold text-zinc-100 tracking-wide font-sans">VinCode</span>
      </div>

      {/* Center: Breadcrumbs / Active Workspace */}
      <div 
        style={{ 
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          maxWidth: '35%',
          pointerEvents: 'none'
        }}
      >
        <div className="flex items-center gap-1.5 text-[12px] text-zinc-400 font-medium truncate font-sans pointer-events-auto">
          <span className="truncate">{breadcrumb}</span>
        </div>
      </div>

      {/* Right: Actions and window overlay padding */}
      <div 
        className="flex items-center gap-2" 
        style={{ WebkitAppRegion: 'no-drag', paddingRight: '160px' } as any}
      >
        {showPill && (
          <button
            onClick={onOpenStats}
            title="Click to view detailed DeepSeek cost & cache efficiency analysis"
            className="flex items-center gap-2 bg-zinc-900 border border-zinc-800/80 text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200 transition-all font-mono"
            style={{
              paddingTop: '0px',
              paddingBottom: '0px',
              paddingLeft: '10px',
              paddingRight: '10px',
              fontSize: '11.5px',
              height: '24px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
            }}
          >
            <span className="text-yellow-500 font-semibold">{(totalInput + totalOutput).toLocaleString()}</span>
            <span className="text-zinc-600">|</span>
            <span className="text-blue-400 font-semibold">{((totalInput / 1000000) * 100).toFixed(3)}%</span>
            <span className="text-zinc-600">|</span>
            <span className="text-emerald-500 font-semibold">${totalCost.toFixed(5)}</span>
          </button>
        )}

        <button className="flex items-center gap-1 px-2 py-1 text-[11px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors font-sans font-medium">
          <ExternalLink size={11} className="text-blue-400" />
          <span>Open IDE</span>
        </button>

        <button 
          onClick={onOpenSettings}
          className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
          title="Settings"
        >
          <Settings size={13} />
        </button>
      </div>
    </header>
  );
}
