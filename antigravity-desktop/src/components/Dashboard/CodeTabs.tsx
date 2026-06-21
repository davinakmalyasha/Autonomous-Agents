import { useState } from 'react';
import type { AgentOutputs } from '../../types';

interface CodeTabsProps {
  outputs: AgentOutputs;
}

interface Tab {
  key: keyof AgentOutputs;
  label: string;
  language: string;
}

const TABS: Tab[] = [
  { key: 'requirements', label: 'Requirements', language: 'markdown' },
  { key: 'gherkin', label: 'Acceptance Criteria', language: 'markdown' },
  { key: 'mermaid', label: 'User Flow', language: 'markdown' },
  { key: 'tech_spec', label: 'Technical Spec', language: 'markdown' },
  { key: 'code', label: 'generated_app.py', language: 'python' },
  { key: 'test_report', label: 'QA Feedback', language: 'markdown' },
  { key: 'devops_config', label: 'Dockerfile', language: 'dockerfile' },
  { key: 'analytics_report', label: 'Analytics Report', language: 'markdown' },
];

export function CodeTabs({ outputs }: CodeTabsProps) {
  const [activeTab, setActiveTab] = useState<Tab>(TABS[0]);

  const activeContent = outputs[activeTab.key] || '// No output yet...';

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div
        className="flex gap-1 overflow-x-auto p-2"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border-color)',
        }}
      >
        {TABS.map((tab) => {
          const hasContent = !!outputs[tab.key];
          const isActive = activeTab.key === tab.key;

          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab)}
              className="px-3 py-1.5 rounded text-xs font-medium whitespace-nowrap transition-colors
                         hover:opacity-80"
              style={{
                backgroundColor: isActive ? 'var(--accent)' : 'transparent',
                color: isActive ? '#fff' : hasContent ? 'var(--text-primary)' : 'var(--text-secondary)',
                opacity: hasContent ? 1 : 0.5,
              }}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Code display */}
      <div
        className="flex-1 overflow-auto p-4 font-mono text-sm"
        style={{
          backgroundColor: 'var(--bg-primary)',
          color: 'var(--text-primary)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {activeContent}
      </div>
    </div>
  );
}
