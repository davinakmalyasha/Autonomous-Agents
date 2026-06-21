import { useState, useEffect } from 'react';
import { getHistory } from '../../api/client';

interface SidebarProps {
  onReset: () => void;
  onSelectPrompt: (prompt: string) => void;
}

const TEMPLATES = [
  { icon: '📊', label: 'SQLite Calculator', prompt: 'Build a terminal-based calculator with history tracking stored in an SQLite database.' },
  { icon: '🔑', label: 'Password DB', prompt: 'Create a Secure Password Manager command-line app with SQLite to store credentials.' },
  { icon: '🌦️', label: 'Weather Fetcher', prompt: 'Generate a Python script that fetches current weather for a city and formats the output.' },
];

export function Sidebar({ onReset, onSelectPrompt }: SidebarProps) {
  const [history, setHistory] = useState<string[]>([]);

  const refreshHistory = async () => {
    try {
      const data = await getHistory();
      setHistory(data.prompts || []);
    } catch {
      setHistory([]);
    }
  };

  useEffect(() => {
    refreshHistory();
  }, []);

  const handleReset = async () => {
    await onReset();
  };

  return (
    <aside
      className="w-56 flex-shrink-0 flex flex-col gap-4 p-4 overflow-y-auto"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border-color)',
      }}
    >
      {/* Workspace */}
      <div>
        <h3
          className="text-xs font-semibold uppercase tracking-wider mb-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          Workspace
        </h3>
        <button
          onClick={handleReset}
          className="w-full px-3 py-2 rounded-lg text-sm font-medium transition-all
                     hover:opacity-80 active:scale-[0.98]"
          style={{
            backgroundColor: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border-color)',
          }}
        >
          🧹 New Session
        </button>
      </div>

      {/* Prompt Templates */}
      <div>
        <h3
          className="text-xs font-semibold uppercase tracking-wider mb-3"
          style={{ color: 'var(--text-secondary)' }}
        >
          Prompt Templates
        </h3>
        <div className="space-y-1.5">
          {TEMPLATES.map((tpl) => (
            <button
              key={tpl.label}
              onClick={() => onSelectPrompt(tpl.prompt)}
              className="w-full px-3 py-2 rounded-lg text-sm text-left transition-all
                         hover:opacity-80 active:scale-[0.98]"
              style={{
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
              }}
            >
              {tpl.icon} {tpl.label}
            </button>
          ))}
        </div>
      </div>

      {/* Recent Prompts */}
      <div className="flex-1">
        <div className="flex items-center justify-between mb-3">
          <h3
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: 'var(--text-secondary)' }}
          >
            Recent Prompts
          </h3>
          <button
            onClick={refreshHistory}
            className="text-xs hover:opacity-70 transition-opacity"
            style={{ color: 'var(--accent)' }}
          >
            🔄
          </button>
        </div>
        <div className="space-y-1">
          {history.length === 0 && (
            <div
              className="text-xs italic px-2 py-1"
              style={{ color: 'var(--text-secondary)' }}
            >
              No recent prompts
            </div>
          )}
          {history.map((prompt, i) => (
            <button
              key={i}
              onClick={() => onSelectPrompt(prompt)}
              className="w-full px-2 py-1.5 rounded text-xs text-left truncate
                         hover:opacity-80 transition-all"
              style={{
                backgroundColor: 'var(--bg-primary)',
                color: 'var(--text-secondary)',
                border: '1px solid transparent',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'transparent';
              }}
            >
              {prompt.length > 40 ? prompt.slice(0, 40) + '...' : prompt}
            </button>
          ))}
        </div>
      </div>
    </aside>
  );
}
