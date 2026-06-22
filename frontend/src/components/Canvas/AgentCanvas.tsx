import { useCanvas } from '../../hooks/useCanvas';
import { useCanvasAgentState } from '../../hooks/useCanvasAgentState';
import CanvasWorkspace from './CanvasWorkspace';
import SubagentDrawer from './SubagentDrawer';
import ChatView from '../Workspace/ChatView';
import type { AppState, ChatMessage, ModelOption } from '../../types';

interface Props {
  messages: ChatMessage[];
  isRunning: boolean;
  workspaceName: string | null;
  chatTitle: string | null;
  selectedModel: string;
  models: ModelOption[];
  state: AppState | null;
  hasActiveChat: boolean;
  notification: string | null;
  onSend: (message: string) => void;
  onCancel: () => void;
  onModelChange: (model: string) => void;
  onClearNotification: () => void;
  workspaceId: string | null;
  chatId: string | null;
}

export default function AgentCanvas(props: Props) {
  const { pan, setPan, zoom, setZoom, selectedNodeId, setSelectedNodeId, getInitialNodes, getInitialEdges } = useCanvas();
  const { steps, nodes, edges } = useCanvasAgentState({
    isRunning: props.isRunning,
    liveLog: props.state?.live_terminal_log,
    getInitialNodes,
    getInitialEdges,
  });

  const selectedNode = nodes.find((n) => n.id === selectedNodeId);
  const selectedNodeSteps = steps.filter((s) => s.agent === selectedNodeId);
  
  const selectedNodeTask = steps
    .filter((s) => s.toolName === 'task' || s.toolName === 'start_async_task')
    .map((s) => {
      try {
        const parsed = JSON.parse(s.args || '{}');
        if (parsed.name === selectedNodeId) return parsed.task;
      } catch {}
      return null;
    })
    .filter(Boolean)[0] || '';

  return (
    <div className="relative flex flex-1 min-w-0 h-full overflow-hidden rounded-xl border border-zinc-800/80 bg-[#0a0a0c]">
      <CanvasWorkspace
        nodes={nodes}
        edges={edges}
        pan={pan}
        zoom={zoom}
        steps={steps}
        selectedId={selectedNodeId}
        setPan={setPan}
        setZoom={setZoom}
        onSelectNode={setSelectedNodeId}
      />

      <ChatView {...props} />

      <SubagentDrawer
        isOpen={!!selectedNodeId && selectedNodeId !== 'Supervisor'}
        subagentName={selectedNodeId}
        status={selectedNode?.status || 'idle'}
        taskDesc={selectedNodeTask}
        steps={selectedNodeSteps}
        workspaceId={props.workspaceId}
        chatId={props.chatId}
        onClose={() => setSelectedNodeId(null)}
      />
    </div>
  );
}
