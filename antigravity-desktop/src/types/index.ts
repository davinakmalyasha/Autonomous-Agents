// ── API Response Types ──────────────────────────────────────────────────────

export type Theme = 'dark' | 'light';

export interface TokenCall {
  agent: string;
  model: string;
  input: number;
  output: number;
  cache_hits?: number;
  cache_misses?: number;
  cost: number;
  timestamp: string;
  where?: string;
}

export interface TokenUsage {
  total_input_tokens: number;
  total_output_tokens: number;
  total_cache_hit_tokens?: number;
  total_cache_miss_tokens?: number;
  total_cost: number;
  calls: TokenCall[];
}

export interface TeamStats {
  input: number;
  output: number;
  cost: number;
}

export interface AgentOutputs {
  requirements: string;
  tech_spec: string;
  code: string;
  test_report: string;
  devops_config: string;
  analytics_report: string;
  gherkin: string;
  mermaid: string;
}

export interface AgentThoughts {
  supervisor: string;
  developer: string;
}

export interface AgentState {
  active_node: string;
  next_agent: string;
  completed_nodes: string[];
  thoughts: AgentThoughts;
  client_request: string;
  outputs: AgentOutputs;
  project_path: string;
  agents_plan: string;
  antigravity_log: string[];
  live_terminal_log: string;
  selected_model: string;
  selected_temp: number;
  failed_models: string[];
  token_usage: TokenUsage;
}

// ── SSE Event Types ─────────────────────────────────────────────────────────

export interface SSEStateEvent {
  event: 'state';
  data: AgentState;
}

export interface SSEErrorEvent {
  event: 'error';
  data: { error: string };
}

export interface SSEDoneEvent {
  event: 'done';
  data: { status: 'complete' | 'error' };
}

export type SSEEvent = SSEStateEvent | SSEErrorEvent | SSEDoneEvent;

// ── API Request Types ───────────────────────────────────────────────────────

export interface RunRequest {
  prompt: string;
  model?: string;
  temperature?: number;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'jarvis' | 'agent';
  text: string;
  timestamp: number;
}

export interface WorkspaceInfo {
  id: string;
  path: string;
  name: string;
  created_at: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  provider: string;
}
