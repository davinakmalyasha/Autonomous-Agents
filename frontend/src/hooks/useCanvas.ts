import { useState, useCallback } from 'react';
import type { CanvasNode, CanvasEdge } from '../types/canvas.types';

const CENTER_X = 1000;
const CENTER_Y = 800;
const RADIUS = 300;

const CIRCLE_AGENTS = ['Dev', 'BA', 'SA', 'DevOps', 'Refinement', 'Analytics', 'Designer'];

const AGENT_LABELS: Record<string, string> = {
  Dev: 'Developer Subagent',
  BA: 'Business Analyst Subagent',
  SA: 'Software Analyst Subagent',
  DevOps: 'DevOps Subagent',
  Refinement: 'Refinement Subagent',
  Analytics: 'Analytics Subagent',
  Critic: 'Evaluation Subagent',
  Designer: 'UI/UX Designer Subagent',
};

export function useCanvas() {
  const [pan, setPan] = useState({ x: -500, y: -400 });
  const [zoom, setZoom] = useState(1);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const getInitialNodes = useCallback((): CanvasNode[] => {
    const nodes: CanvasNode[] = [
      { id: 'Supervisor', label: 'Supervisor', type: 'supervisor', status: 'idle', x: CENTER_X, y: CENTER_Y }
    ];

    CIRCLE_AGENTS.forEach((name, i) => {
      const angle = (i * 2 * Math.PI) / CIRCLE_AGENTS.length;
      nodes.push({
        id: name,
        label: AGENT_LABELS[name] || name,
        type: 'subagent',
        status: 'idle',
        x: Math.round(CENTER_X + RADIUS * Math.cos(angle)),
        y: Math.round(CENTER_Y + RADIUS * Math.sin(angle)),
      });
    });

    // Dev node is positioned directly to the right of Supervisor: Dev.angle = 0 => x = CENTER_X + RADIUS, y = CENTER_Y.
    // Position Critic (Evaluation Subagent) right next to it:
    nodes.push({
      id: 'Critic',
      label: AGENT_LABELS['Critic'],
      type: 'subagent',
      status: 'idle',
      x: CENTER_X + RADIUS + 265,
      y: CENTER_Y,
    });

    return nodes;
  }, []);

  const getInitialEdges = useCallback((): CanvasEdge[] => {
    const edges = CIRCLE_AGENTS.map((name) => ({
      id: `edge-Supervisor-${name}`,
      from: 'Supervisor',
      to: name,
      active: false,
    }));

    // Connect Critic to Dev instead of Supervisor
    edges.push({
      id: 'edge-Dev-Critic',
      from: 'Dev',
      to: 'Critic',
      active: false,
    });

    return edges;
  }, []);

  const handleZoom = useCallback((factor: number) => {
    setZoom((z) => Math.max(0.3, Math.min(2.5, z * factor)));
  }, []);

  const handleReset = useCallback(() => {
    setPan({ x: -500, y: -400 });
    setZoom(1);
  }, []);

  return {
    pan,
    setPan,
    zoom,
    setZoom,
    selectedNodeId,
    setSelectedNodeId,
    getInitialNodes,
    getInitialEdges,
    handleZoom,
    handleReset,
  };
}
