import { useState, useEffect, useCallback } from 'react';
import { AgentProvider } from './context/AgentContext';
import { Header } from './components/Layout/Header';
import { Sidebar } from './components/Layout/Sidebar';
import { ChatPanel } from './components/Chat/ChatPanel';
import { AgentStatus } from './components/Dashboard/AgentStatus';
import { TokenStats } from './components/Dashboard/TokenStats';
import { CodeTabs } from './components/Dashboard/CodeTabs';
import { ModelSelector } from './components/Dashboard/ModelSelector';
import { useAgentState } from './hooks/useAgentState';
import {
  getStoredTheme,
  applyTheme,
  toggleTheme as toggleThemeUtil,
} from './hooks/useTheme';
import type { Theme } from './types';

function AppContent() {
  const [theme, setTheme] = useState<Theme>(getStoredTheme);
  const { state, runPrompt, resetSession } = useAgentState();

  // Apply theme on mount
  useEffect(() => {
    applyTheme(theme);
  }, []);

  const handleToggleTheme = useCallback(() => {
    setTheme((prev) => toggleThemeUtil(prev));
  }, []);

  const handleReset = useCallback(async () => {
    await resetSession();
  }, [resetSession]);

  const handleSelectPrompt = useCallback(
    (prompt: string) => {
      runPrompt(prompt, state.selected_model, state.selected_temp);
    },
    [runPrompt, state.selected_model, state.selected_temp],
  );

  const handleModelChange = useCallback(
    (model: string) => {
      // Model is set via runPrompt — stored in context for display
      // We update it lazily — next runPrompt call picks it up
      state.selected_model = model;
    },
    [state],
  );

  const handleTempChange = useCallback(
    (temp: number) => {
      state.selected_temp = temp;
    },
    [state],
  );

  return (
    <div
      className="flex flex-col h-screen w-screen overflow-hidden"
      style={{ backgroundColor: 'var(--bg-primary)' }}
    >
      {/* Header */}
      <Header theme={theme} onToggleTheme={handleToggleTheme} />

      {/* Body: Sidebar + Chat + Right Panel */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Sidebar */}
        <Sidebar onReset={handleReset} onSelectPrompt={handleSelectPrompt} />

        {/* Center: Chat Panel + Code Tabs */}
        <div className="flex flex-col flex-1 overflow-hidden">
          {/* Code Tabs (top half) */}
          <div className="flex-1 overflow-hidden">
            <CodeTabs outputs={state.outputs} />
          </div>

          {/* Chat Panel (bottom half) */}
          <div
            className="flex-shrink-0"
            style={{ height: '45%', borderTop: '1px solid var(--border-color)' }}
          >
            <ChatPanel />
          </div>
        </div>

        {/* Right Sidebar: Status + Stats + Settings */}
        <aside
          className="w-56 flex-shrink-0 flex flex-col gap-4 p-4 overflow-y-auto"
          style={{
            backgroundColor: 'var(--bg-secondary)',
            borderLeft: '1px solid var(--border-color)',
          }}
        >
          <AgentStatus state={state} />
          <TokenStats tokenUsage={state.token_usage} />
          <ModelSelector
            model={state.selected_model}
            temperature={state.selected_temp}
            onModelChange={handleModelChange}
            onTempChange={handleTempChange}
          />
        </aside>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AgentProvider>
      <AppContent />
    </AgentProvider>
  );
}
