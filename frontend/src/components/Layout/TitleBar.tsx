import { Minus, Square, X } from 'lucide-react';

const MENUS = ['Antigravity', 'File', 'View', 'Window'];

interface Props {
  onMenuClick?: (menu: string) => void;
}

export default function TitleBar({ onMenuClick }: Props) {
  return (
    <header className="flex items-center justify-between select-none flex-shrink-0 h-8 bg-[#161616] border-b border-zinc-800 px-2">
      {/* Left: Application menus — low-contrast white, ~13px */}
      <div className="flex items-center">
        {MENUS.map((menu) => (
          <button
            key={menu}
            onClick={() => onMenuClick?.(menu)}
            className="px-2.5 py-0.5 text-[13px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/70 rounded transition-colors cursor-default leading-none"
          >
            {menu}
          </button>
        ))}
      </div>

      {/* Right: Window action icons (minimize, maximize, close) */}
      <div className="flex items-center">
        <button
          className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
          aria-label="Minimize"
          title="Minimize"
        >
          <Minus size={12} strokeWidth={2} />
        </button>
        <button
          className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors"
          aria-label="Maximize"
          title="Maximize"
        >
          <Square size={11} strokeWidth={2} />
        </button>
        <button
          className="p-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-900/40 rounded transition-colors"
          aria-label="Close"
          title="Close"
        >
          <X size={12} strokeWidth={2} />
        </button>
      </div>
    </header>
  );
}
