import type { AgentState } from '../../types';

interface AgentStatusProps {
  state: AgentState;
}

export function AgentStatus({ state }: AgentStatusProps) {
  const { active_node, next_agent, completed_nodes, thoughts } = state;

  return (
    <div
      className="p-4 rounded-lg space-y-3"
      style={{
        backgroundColor: 'var(--bg-secondary)',
        border: '1px solid var(--border-color)',
      }}
    >
      <h3
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: 'var(--text-secondary)' }}
      >
        Agent Status
      </h3>

      {/* Active Node */}
      <div className="flex items-center gap-2">
        <div
          className={`w-2 h-2 rounded-full ${
            active_node ? 'animate-pulse' : ''
          }`}
          style={{
            backgroundColor: active_node ? 'var(--success)' : 'var(--border-color)',
          }}
        />
        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
          {active_node ? active_node.toUpperCase() : 'Idle'}
        </span>
        {active_node && (
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: 'var(--accent)',
              color: '#fff',
            }}
          >
            Running
          </span>
        )}
      </div>

      {/* Next Agent */}
      {next_agent && next_agent !== 'finish' && (
        <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
          Next: <span style={{ color: 'var(--accent)', fontWeight: 600 }}>{next_agent.toUpperCase()}</span>
        </div>
      )}

      {/* Completed Nodes */}
      {completed_nodes.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
            Completed:
          </div>
          {completed_nodes.map((node) => (
            <div
              key={node}
              className="text-xs flex items-center gap-1.5"
              style={{ color: 'var(--success)' }}
            >
              ✅ {node.toUpperCase()}
            </div>
          ))}
        </div>
      )}

      {/* Current Thought */}
      {thoughts.supervisor && (
        <div
          className="text-xs italic p-2 rounded"
          style={{
            backgroundColor: 'var(--bg-primary)',
            color: 'var(--text-secondary)',
            borderLeft: '2px solid var(--accent)',
          }}
        >
          "{thoughts.supervisor.slice(0, 200)}{thoughts.supervisor.length > 200 ? '...' : ''}"
        </div>
      )}
    </div>
  );
}
