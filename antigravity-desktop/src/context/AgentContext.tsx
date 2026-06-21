import { createContext, useContext, useReducer, type ReactNode } from 'react';
import type { AgentState, TokenUsage, AgentOutputs } from '../types';

// ── Default State ───────────────────────────────────────────────────────────

const emptyOutputs: AgentOutputs = {
  requirements: '',
  tech_spec: '',
  code: '',
  test_report: '',
  devops_config: '',
  analytics_report: '',
  gherkin: '',
  mermaid: '',
};

const emptyTokenUsage: TokenUsage = {
  total_input_tokens: 0,
  total_output_tokens: 0,
  total_cost: 0,
  calls: [],
};

function createDefaultState(): AgentState {
  return {
    active_node: '',
    next_agent: '',
    completed_nodes: [],
    thoughts: { supervisor: '', developer: '' },
    client_request: '',
    outputs: { ...emptyOutputs },
    project_path: '',
    agents_plan: '',
    antigravity_log: [],
    live_terminal_log: '',
    selected_model: 'Automatic Fallback',
    selected_temp: 0.7,
    failed_models: [],
    token_usage: { ...emptyTokenUsage },
  };
}

// ── Action Types ────────────────────────────────────────────────────────────

type Action =
  | { type: 'SET_STATE'; payload: Partial<AgentState> }
  | { type: 'RESET' }
  | { type: 'SET_ERROR'; payload: string };

// ── Reducer ─────────────────────────────────────────────────────────────────

function agentReducer(state: AgentState, action: Action): AgentState {
  switch (action.type) {
    case 'SET_STATE':
      return {
        ...state,
        ...action.payload,
        outputs: action.payload.outputs
          ? { ...state.outputs, ...action.payload.outputs }
          : state.outputs,
        thoughts: action.payload.thoughts
          ? { ...state.thoughts, ...action.payload.thoughts }
          : state.thoughts,
        token_usage: action.payload.token_usage
          ? { ...action.payload.token_usage }
          : state.token_usage,
      };
    case 'RESET':
      return createDefaultState();
    case 'SET_ERROR':
      return {
        ...state,
        live_terminal_log: `❌ ${action.payload}\n`,
      };
    default:
      return state;
  }
}

// ── Context ─────────────────────────────────────────────────────────────────

interface AgentContextValue {
  state: AgentState;
  dispatch: React.Dispatch<Action>;
}

const AgentContext = createContext<AgentContextValue | null>(null);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(agentReducer, undefined, createDefaultState);

  return (
    <AgentContext.Provider value={{ state, dispatch }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgentContext() {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error('useAgentContext must be used within AgentProvider');
  return ctx;
}
