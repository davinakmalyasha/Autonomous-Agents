import { ThemeToggle } from './ThemeToggle';
import type { Theme } from '../../types';

interface HeaderProps {
  theme: Theme;
  onToggleTheme: () => void;
}

export function Header({ theme, onToggleTheme }: HeaderProps) {
  return (
    <header
      className="flex items-center justify-between px-5 py-3 flex-shrink-0 select-none"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
      }}
    >
      <div className="flex items-center gap-3">
        <span className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>
          🤖 Antigravity
        </span>
        <span
          className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--accent)',
          }}
        >
          Virtual IT Department
        </span>
      </div>

      <div className="flex items-center gap-3">
        <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Agent Workspace
        </span>
        <ThemeToggle theme={theme} onToggle={onToggleTheme} />
      </div>
    </header>
  );
}
