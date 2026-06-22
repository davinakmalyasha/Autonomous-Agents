import { useMemo } from 'react';
import type { CanvasNode, CanvasEdge } from '../types/canvas.types';
import { parseLogToSteps } from '../utils/logParser';

interface Input {
  isRunning: boolean;
  liveLog: string | undefined;
  getInitialNodes: () => CanvasNode[];
  getInitialEdges: () => CanvasEdge[];
}

export function useCanvasAgentState({ isRunning, liveLog, getInitialNodes, getInitialEdges }: Input) {
  const steps = useMemo(() => {
    if (!liveLog) return [];
    return parseLogToSteps(liveLog).steps;
  }, [liveLog]);

  const activeAgent = useMemo(() => {
    if (!isRunning) return null;
    if (steps.length === 0) return 'Supervisor';
    const lastStep = steps[steps.length - 1];
    if (lastStep.toolName === 'task' || lastStep.toolName === 'start_async_task') {
      try {
        const parsed = JSON.parse(lastStep.args || '{}');
        if (parsed.name) return parsed.name;
      } catch {}
    }
    return lastStep.agent || 'Supervisor';
  }, [isRunning, steps]);

  const nodes = useMemo(() => {
    const base = getInitialNodes();
    return base.map((node) => {
      let status: 'idle' | 'working' | 'completed' | 'failed' = 'idle';
      if (node.id === 'Supervisor') {
        status = isRunning && activeAgent === 'Supervisor' ? 'working' : isRunning ? 'idle' : 'completed';
      } else {
        if (activeAgent === node.id) {
          status = 'working';
        } else if (steps.some((s) => s.agent === node.id)) {
          status = 'completed';
        }
      }
      
      const agentSteps = steps.filter((s) => s.agent === node.id || (node.id === 'Supervisor' && s.agent === 'Supervisor'));
      const lastStep = agentSteps[agentSteps.length - 1];
      const lastStepText = lastStep ? (lastStep.title || lastStep.toolName) : undefined;

      return { ...node, status, lastStepText };
    });
  }, [getInitialNodes, isRunning, activeAgent, steps]);

  const edges = useMemo(() => {
    const base = getInitialEdges();
    return base.map((edge) => ({
      ...edge,
      active: isRunning && activeAgent === edge.to,
    }));
  }, [getInitialEdges, isRunning, activeAgent]);

  return { steps, activeAgent, nodes, edges };
}
