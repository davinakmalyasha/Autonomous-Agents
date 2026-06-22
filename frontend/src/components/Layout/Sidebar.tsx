import { useState, useEffect, useCallback } from 'react';
import { PanelLeftClose, FolderPlus, Settings } from 'lucide-react';
import { fetchWorkspaces, addWorkspace, removeWorkspace, fetchChats, createChat, deleteChat, fetchChat } from '../../services/api';
import type { WorkspaceInfo, ChatSummary, ChatData } from '../../types';
import SidebarProjectList from './SidebarProjectList';
import SidebarAddFolderModal from './SidebarAddFolderModal';

interface Props {
  activeWorkspaceId: string | null;
  activeChatId: string | null;
  collapsed: boolean;
  onSelectWorkspace: (ws: WorkspaceInfo) => void;
  onSelectChat: (ws: WorkspaceInfo, chat: ChatData) => void;
  onToggleCollapse: () => void;
  onOpenSettings: () => void;
}

export default function Sidebar({
  activeWorkspaceId, activeChatId, collapsed,
  onSelectWorkspace, onSelectChat, onToggleCollapse, onOpenSettings,
}: Props) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [expandedWs, setExpandedWs] = useState<Set<string>>(new Set());
  const [chatMap, setChatMap] = useState<Record<string, ChatSummary[]>>({});
  const [showAddWs, setShowAddWs] = useState(false);
  const [newWsPath, setNewWsPath] = useState('');

  const loadWorkspaces = useCallback(async () => {
    const ws = await fetchWorkspaces();
    setWorkspaces(ws);
    setExpandedWs((prev) => {
      const next = new Set(prev);
      ws.forEach((w) => next.add(w.id));
      return next;
    });
    for (const w of ws) {
      const chats = await fetchChats(w.id);
      setChatMap((prev) => ({ ...prev, [w.id]: chats }));
    }
    return ws;
  }, []);

  useEffect(() => {
    loadWorkspaces();
  }, [loadWorkspaces]);

  const toggleWs = useCallback(async (ws: WorkspaceInfo) => {
    setExpandedWs((prev) => {
      const next = new Set(prev);
      if (next.has(ws.id)) next.delete(ws.id);
      else next.add(ws.id);
      return next;
    });
    onSelectWorkspace(ws);
    if (!chatMap[ws.id]) {
      const chats = await fetchChats(ws.id);
      setChatMap((prev) => ({ ...prev, [ws.id]: chats }));
    }
  }, [chatMap, onSelectWorkspace]);

  const handleAddWorkspace = async () => {
    if ((window as any).antigravity?.selectFolder) {
      try {
        const folderPath = await (window as any).antigravity.selectFolder();
        if (!folderPath) return;
        const name = folderPath.split('\\').pop() || folderPath.split('/').pop() || '';
        await addWorkspace(folderPath, name);
        await loadWorkspaces();
        return;
      } catch {}
    }
    setNewWsPath('');
    setShowAddWs(true);
  };

  const handleCreateChat = async (ws: WorkspaceInfo) => {
    const chat = await createChat(ws.id, 'New Conversation');
    const chats = await fetchChats(ws.id);
    setChatMap((prev) => ({ ...prev, [ws.id]: chats }));
    const fullChat = await fetchChat(ws.id, chat.id);
    onSelectChat(ws, fullChat);
  };

  const handleDeleteChat = async (e: React.MouseEvent, ws: WorkspaceInfo, chatId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    await deleteChat(ws.id, chatId);
    const chats = await fetchChats(ws.id);
    setChatMap((prev) => ({ ...prev, [ws.id]: chats }));
  };

  const handleSelectChat = async (ws: WorkspaceInfo, chatId: string) => {
    const chat = await fetchChat(ws.id, chatId);
    onSelectChat(ws, chat);
  };

  const relativeTime = (iso: string) => {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'now';
    if (mins < 60) return `${mins}m`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h`;
    return `${Math.floor(hrs / 24)}d`;
  };

  const submitAddWs = async () => {
    if (!newWsPath.trim()) return;
    await addWorkspace(newWsPath.trim());
    setNewWsPath('');
    setShowAddWs(false);
    await loadWorkspaces();
  };

  return (
    <aside
      className="flex flex-col flex-shrink-0 select-none backdrop-blur-md border rounded-xl shadow-lg overflow-hidden transition-all duration-300 ease-in-out"
      style={{ 
        width: collapsed ? 56 : 280, 
        backgroundColor: 'rgba(20, 20, 23, 0.65)', 
        borderColor: 'rgba(63, 63, 70, 0.45)' 
      }}
    >
      {collapsed ? (
        <div className="flex flex-col items-center py-4 gap-4 h-full">
          <button onClick={onToggleCollapse} className="w-10 h-10 flex items-center justify-center text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 rounded-xl transition-all cursor-pointer">
            <PanelLeftClose size={16} />
          </button>
          <button onClick={handleAddWorkspace} className="w-10 h-10 flex items-center justify-center text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 rounded-xl transition-all cursor-pointer" title="Add Workspace">
            <FolderPlus size={16} />
          </button>
          <div className="flex-1" />
          <button onClick={onOpenSettings} className="w-10 h-10 flex items-center justify-center text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60 rounded-xl transition-all cursor-pointer" title="Settings">
            <Settings size={16} />
          </button>
        </div>
      ) : (
        <div className="flex flex-col h-full overflow-hidden">
          <div className="flex items-center justify-between" style={{ padding: '14px 16px 6px 16px' }}>
            <span className="text-[11px] font-bold text-zinc-500 uppercase tracking-widest">Workspace</span>
            <button onClick={onToggleCollapse} className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors" title="Close Sidebar">
              <PanelLeftClose size={16} />
            </button>
          </div>

          <div className="px-3 py-2" style={{ marginBottom: '12px' }}>
            <button onClick={handleAddWorkspace} className="flex items-center justify-center gap-2 w-full text-[13px] font-semibold text-zinc-200 hover:text-white bg-zinc-800/70 border border-zinc-700/65 py-2 px-4 rounded-lg cursor-pointer hover:bg-zinc-700/70 hover:border-zinc-600/80 transition-all shadow-sm">
              <FolderPlus size={14} className="text-zinc-300" />
              <span>Add Folder</span>
            </button>
          </div>

          <SidebarProjectList
            workspaces={workspaces}
            expandedWs={expandedWs}
            chatMap={chatMap}
            activeWorkspaceId={activeWorkspaceId}
            activeChatId={activeChatId}
            toggleWs={toggleWs}
            handleCreateChat={handleCreateChat}
            removeWorkspace={removeWorkspace}
            loadWorkspaces={loadWorkspaces}
            handleDeleteChat={handleDeleteChat}
            handleSelectChat={handleSelectChat}
            relativeTime={relativeTime}
            handleAddWorkspace={handleAddWorkspace}
          />

          <div style={{ borderTop: '1px solid rgba(63, 63, 70, 0.25)', padding: '6px 8px' }}>
            <button onClick={onOpenSettings} className="flex items-center gap-2.5 w-full text-[13px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors" style={{ padding: '8px 12px', textAlign: 'left' }}>
              <Settings size={15} className="text-zinc-550 flex-shrink-0" />
              <span>Settings</span>
            </button>
          </div>
        </div>
      )}

      <SidebarAddFolderModal
        isOpen={showAddWs}
        value={newWsPath}
        onChange={setNewWsPath}
        onClose={() => setShowAddWs(false)}
        onSubmit={submitAddWs}
      />
    </aside>
  );
}
