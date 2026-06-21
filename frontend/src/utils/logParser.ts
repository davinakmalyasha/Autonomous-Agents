// Log parser utility for Antigravity trace visualization

export interface TraceStep {
  id: string;
  type: 'thought' | 'tool' | 'command' | 'system';
  agent: string;
  title: string;
  content: string;
  toolName?: string;
  args?: string;
  isError?: boolean;
}

export interface GroupedTraceStep {
  id: string;
  type: 'thought' | 'exploration' | 'edit' | 'command' | 'system';
  title: string;
  agent: string;
  steps: TraceStep[];
  isError?: boolean;
}

/** Parses the full raw live_terminal_log into steps and final response */
export function parseLogToSteps(log: string): { steps: TraceStep[]; assistantResponse: string | null } {
  const lines = log.split('\n');
  const steps: TraceStep[] = [];
  let assistantResponse: string | null = null;
  let currentStep: TraceStep | null = null;
  let stepCounter = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    if (trimmed.startsWith('[THOUGHT]')) {
      const match = trimmed.match(/^\[THOUGHT\]\s+\[([^\]]+)\]\s+(.*)$/);
      if (match) {
        currentStep = {
          id: `step-${stepCounter++}`,
          type: 'thought',
          agent: match[1],
          title: `${match[1]} Thought`,
          content: match[2],
        };
        steps.push(currentStep);
      }
    } else if (trimmed.startsWith('🧠')) {
      // Real-time developer status messages
      const match = trimmed.match(/^🧠\s+(\w+):\s+(.*)$/);
      if (match) {
        currentStep = {
          id: `step-${stepCounter++}`,
          type: 'thought',
          agent: match[1],
          title: `${match[1]} Thinking`,
          content: match[2],
        };
        steps.push(currentStep);
      }
    } else if (trimmed.includes('🔧 Calling')) {
      const match = trimmed.match(/🔧 Calling\s+(\w+)\((.*)\)/);
      if (match) {
        const tool = match[1];
        let args = match[2];
        // Try to parse as JSON for cleaner field extraction in display
        try {
          const parsed = JSON.parse(args);
          // Store structured args — keep file_path, pattern, command for display
          args = JSON.stringify(parsed);
        } catch {
          // Not valid JSON — keep raw args string but truncate if huge
          if (args.length > 500) args = args.substring(0, 500) + '...';
        }
        currentStep = {
          id: `step-${stepCounter++}`,
          type: tool === 'run_command' ? 'command' : 'tool',
          agent: 'Developer',
          title: tool === 'run_command' ? 'Running command' : `Calling ${tool}`,
          toolName: tool,
          args,
          content: '',
        };
        steps.push(currentStep);
      }
    } else if (trimmed.startsWith('[TOOL]')) {
      // Skip TOOL header prefix line
    } else if (trimmed.startsWith('🤖 Assistant:')) {
      assistantResponse = trimmed.slice(13).trim();
      currentStep = null;
    } else if (trimmed.startsWith('🤖 Supervisor:')) {
      currentStep = null;
    } else if (trimmed.startsWith('👤 User:') || trimmed.startsWith('🧹 Session')) {
      currentStep = null;
    } else {
      if (assistantResponse !== null && currentStep === null) {
        assistantResponse += '\n' + trimmed;
      } else if (currentStep) {
        currentStep.content += (currentStep.content ? '\n' : '') + trimmed;
        if (currentStep.content.includes('[ERR]') || currentStep.content.includes('Error:')) {
          currentStep.isError = true;
        }
      }
    }
  }

  return { steps, assistantResponse };
}

/** Groups consecutive exploration/edit tool steps for visual summary */
export function groupTraceSteps(steps: TraceStep[]): GroupedTraceStep[] {
  const grouped: GroupedTraceStep[] = [];
  let currentGroup: GroupedTraceStep | null = null;
  let groupCounter = 0;

  for (const step of steps) {
    if (step.type === 'tool') {
      const isEdit = step.toolName === 'write_file' || step.toolName === 'edit_file';
      const expectedType = isEdit ? 'edit' : 'exploration';

      if (currentGroup && currentGroup.type === expectedType) {
        currentGroup.steps.push(step);
        if (step.isError) currentGroup.isError = true;
        
        // Update title with count
        const count = currentGroup.steps.length;
        currentGroup.title = isEdit
          ? `Edited ${count} file${count > 1 ? 's' : ''}`
          : `Explored ${count} file${count > 1 ? 's' : ''}`;
      } else {
        currentGroup = {
          id: `group-${groupCounter++}`,
          type: expectedType,
          title: isEdit ? 'Edited 1 file' : 'Explored 1 file',
          agent: step.agent,
          steps: [step],
          isError: step.isError,
        };
        grouped.push(currentGroup);
      }
    } else {
      currentGroup = {
        id: step.id,
        type: step.type === 'command' ? 'command' : step.type === 'thought' ? 'thought' : 'system',
        title: step.title,
        agent: step.agent,
        steps: [step],
        isError: step.isError,
      };
      grouped.push(currentGroup);
      currentGroup = null; // Break grouping
    }
  }

  return grouped;
}
