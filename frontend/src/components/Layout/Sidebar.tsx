import { useState, useEffect, useCallback } from 'react';
import {
  ArrowLeft, ArrowRight, PanelLeftClose,
  Plus, MessageSquare, Clock, Trash2,
  Folder, ChevronRight, ChevronDown,
  FolderPlus, Settings, FolderOpen,
  SlidersHorizontal,
} from 'lucide-react';
import {
  fetchWorkspaces, addWorkspace, removeWorkspace,
  fetchChats, createChat, deleteChat, fetchChat,
} from '../../services/api';
import type { WorkspaceInfo, ChatSummary, ChatData } from '../../types';

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
  activeWorkspaceId,
  activeChatId,
  collapsed,
  onSelectWorkspace,
  onSelectChat,
  onToggleCollapse,
  onOpenSettings,
}: Props) {
  const [workspaces, setWorkspaces] = useState<WorkspaceInfo[]>([]);
  const [expandedWs, setExpandedWs] = useState<Set<string>>(new Set());
  const [chatMap, setChatMap] = useState<Record<string, ChatSummary[]>>({});
  const [showAddWs, setShowAddWs] = useState(false);
  const [newWsPath, setNewWsPath] = useState('');

  // ── Load workspaces ──
  const loadWorkspaces = useCallback(async () => {
    const ws = await fetchWorkspaces();
    setWorkspaces(ws);
    // Auto-expand all
    setExpandedWs((prev) => {
      const next = new Set(prev);
      ws.forEach((w) => next.add(w.id));
      return next;
    });
    // Load chats for each
    for (const w of ws) {
      const chats = await fetchChats(w.id);
      setChatMap((prev) => ({ ...prev, [w.id]: chats }));
    }
    return ws;
  }, []);

  useEffect(() => {
    let cancelled = false;
    let attempts = 0;

    const tryLoad = async () => {
      while (!cancelled && attempts < 10) {
        const ws = await loadWorkspaces();
        if (ws.length > 0) return; // success — workspaces loaded
        attempts++;
        if (attempts < 10) {
          await new Promise(r => setTimeout(r, 2000)); // wait 2s between polls
        }
      }
    };

    tryLoad();
    return () => { cancelled = true; };
  }, [loadWorkspaces]);


  // ── Toggle workspace expand/collapse ──
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

  // ── Add workspace (Electron native dialog or text modal fallback) ──
  const handleAddWorkspace = async () => {
    if ((window as any).antigravity?.selectFolder) {
      try {
        const folderPath: string = await (window as any).antigravity.selectFolder();
        if (!folderPath) return;
        const name = folderPath.split('\\').pop() || folderPath.split('/').pop() || '';
        await addWorkspace(folderPath, name);
        await loadWorkspaces();
        return;
      } catch { /* fall through to text modal */ }
    }
    setNewWsPath('');
    setShowAddWs(true);
  };

  // ── Create a new conversation (chat) in the active workspace ──
  const handleNewConversation = async () => {
    // If there's only one workspace, auto-select it; otherwise show a prompt
    const targetWs = workspaces.length === 1
      ? workspaces[0]
      : workspaces.find((w) => w.id === activeWorkspaceId);

    if (!targetWs) {
      // No workspaces yet — prompt to add one first
      await handleAddWorkspace();
      return;
    }

    try {
      const chat = await createChat(targetWs.id, 'New Conversation');
      const chats = await fetchChats(targetWs.id);
      setChatMap((prev) => ({ ...prev, [targetWs.id]: chats }));
      const fullChat = await fetchChat(targetWs.id, chat.id);
      onSelectChat(targetWs, fullChat);
    } catch (e) {
      alert(`Failed to create conversation: ${e}`);
    }
  };

  // ── Create chat inside a specific workspace (from the + icon) ──
  const handleCreateChat = async (ws: WorkspaceInfo) => {
    try {
      const chat = await createChat(ws.id, 'New Conversation');
      const chats = await fetchChats(ws.id);
      setChatMap((prev) => ({ ...prev, [ws.id]: chats }));
      const fullChat = await fetchChat(ws.id, chat.id);
      onSelectChat(ws, fullChat);
    } catch (e) {
      alert(`Failed to create conversation: ${e}`);
    }
  };

  // ── Delete chat ──
  const handleDeleteChat = async (e: React.MouseEvent, ws: WorkspaceInfo, chatId: string) => {
    e.stopPropagation();
    if (!confirm('Delete this conversation?')) return;
    try {
      await deleteChat(ws.id, chatId);
      const chats = await fetchChats(ws.id);
      setChatMap((prev) => ({ ...prev, [ws.id]: chats }));
    } catch (err) {
      alert(`Failed to delete: ${err}`);
    }
  };

  // ── Select a chat ──
  const handleSelectChat = async (ws: WorkspaceInfo, chatId: string) => {
    try {
      const chat = await fetchChat(ws.id, chatId);
      onSelectChat(ws, chat);
    } catch (e) {
      alert(`Failed to load conversation: ${e}`);
    }
  };

  // ── Relative time formatter ──
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

  // ── Collapsed state ──
  if (collapsed) {
    return (
      <aside
        className="flex flex-col items-center gap-3 flex-shrink-0 bg-zinc-900 border-r border-zinc-800 pt-2"
        style={{ width: 48 }}
      >
        <button onClick={onToggleCollapse} className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors">
          <PanelLeftClose size={16} />
        </button>
        <button onClick={handleNewConversation} className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors" title="New Conversation">
          <Plus size={16} />
        </button>
        <button onClick={handleAddWorkspace} className="p-1.5 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors" title="Add Workspace">
          <FolderPlus size={16} />
        </button>
        <div className="flex-1" />
        <button className="p-1.5 mb-2 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors" title="Settings">
          <Settings size={16} />
        </button>
      </aside>
    );
  }

  // ── Expanded state ──
  return (
    <aside
      className="flex flex-col flex-shrink-0 select-none bg-zinc-900 border-r border-zinc-800"
      style={{ width: 280 }}
    >
      {/* ═══════ Top navigation bar ═══════ */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
        <div className="flex items-center gap-1.5">
          <button className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors">
            <ArrowLeft size={14} />
          </button>
          <button className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors">
            <ArrowRight size={14} />
          </button>
        </div>
        <button onClick={onToggleCollapse} className="p-1 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded transition-colors">
          <PanelLeftClose size={14} />
        </button>
      </div>

      {/* ═══════ Quick action menu items ═══════ */}
      <div className="px-3 py-2 space-y-0.5">
        <button className="flex items-center gap-2.5 w-full px-3 py-1.5 text-[13px] text-zinc-300 hover:bg-zinc-800/80 rounded-md transition-colors">
          <MessageSquare size={15} className="text-zinc-500 flex-shrink-0" />
          <span>Conversation History</span>
        </button>
        <button className="flex items-center gap-2.5 w-full px-3 py-1.5 text-[13px] text-zinc-300 hover:bg-zinc-800/80 rounded-md transition-colors">
          <Clock size={15} className="text-zinc-500 flex-shrink-0" />
          <span>Scheduled Tasks</span>
        </button>
      </div>

      {/* ═══════ + New Conversation — prominent full-width button ═══════ */}
      <div className="px-3 py-2">
        <button
          onClick={handleNewConversation}
          className="flex items-center justify-center gap-2 w-full px-3 py-2 text-[13px] font-medium text-zinc-200 bg-zinc-800/50 hover:bg-zinc-800 border border-zinc-700/80 hover:border-zinc-600 rounded-lg transition-colors"
        >
          <Plus size={15} className="text-zinc-400" />
          <span>New Conversation</span>
        </button>
      </div>

      {/* ═══════ Projects accordion section ═══════ */}
      <div className="flex-1 flex flex-col min-h-0 mt-1">
        {/* Section header */}
        <div className="flex items-center justify-between px-3 py-1.5">
          <span className="text-[10px] font-semibold text-zinc-500 uppercase tracking-widest">Projects</span>
          <div className="flex items-center gap-1">
            <button className="p-0.5 text-zinc-500 hover:text-zinc-300 rounded transition-colors" title="Filter & sort">
              <SlidersHorizontal size={12} />
            </button>
            <button
              onClick={handleAddWorkspace}
              className="p-0.5 text-zinc-500 hover:text-zinc-300 rounded transition-colors"
              title="Create folder"
            >
              <FolderPlus size={12} />
            </button>
          </div>
        </div>

        {/* Folder / workspace tree */}
        <div className="flex-1 overflow-y-auto px-2">
          {workspaces.map((ws) => {
            const isExpanded = expandedWs.has(ws.id);
            const isActive = ws.id === activeWorkspaceId;
            const chats = chatMap[ws.id] || [];

            return (
              <div key={ws.id} className="mb-0.5">
                {/* ── Workspace / folder header ── */}
                <div className="flex items-center gap-0 group">
                  <button
                    onClick={() => toggleWs(ws)}
                    className={`flex items-center gap-1.5 flex-1 px-2 py-1 text-[12px] rounded-md transition-colors text-left min-w-0 ${
                      isActive
                        ? 'bg-zinc-800 text-zinc-100'
                        : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                    }`}
                  >
                    {isExpanded ? (
                      <ChevronDown size={12} className="text-zinc-500 flex-shrink-0" />
                    ) : (
                      <ChevronRight size={12} className="text-zinc-500 flex-shrink-0" />
                    )}
                    <Folder size={13} className="text-zinc-500 flex-shrink-0" />
                    <span className="truncate font-medium">{ws.name}</span>
                    <span className="text-[10px] text-zinc-600 ml-auto flex-shrink-0">{chats.length}</span>
                  </button>
                  {/* New chat + button (appears on hover) */}
                  <button
                    onClick={(e) => { e.stopPropagation(); handleCreateChat(ws); }}
                    className="p-0.5 text-zinc-600 hover:text-zinc-300 opacity-0 group-hover:opacity-100 transition-all rounded"
                    title="New conversation"
                  >
                    <Plus size={11} />
                  </button>
                  {/* Remove workspace button (appears on hover) */}
                  <button
                    onClick={(e) => { e.stopPropagation(); removeWorkspace(ws.id).then(loadWorkspaces); }}
                    className="p-0.5 text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded"
                    title="Remove project"
                  >
                    <Trash2 size={10} />
                  </button>
                </div>

                {/* ── Chat list (conversations) ── */}
                {isExpanded && (
                  <div className="ml-4 border-l border-zinc-800/60">
                    {chats.length === 0 ? (
                      <div
                        className="px-3 py-3 text-[11px] text-zinc-600 italic cursor-pointer hover:text-zinc-400 transition-colors"
                        onClick={() => handleCreateChat(ws)}
                      >
                        No conversations yet
                      </div>
                    ) : (
                      chats.map((chat) => {
                        const isChatActive = chat.id === activeChatId && ws.id === activeWorkspaceId;
                        return (
                          <div
                            key={chat.id}
                            role="button"
                            tabIndex={0}
                            onClick={() => handleSelectChat(ws, chat.id)}
                            onKeyDown={(e) => { if (e.key === 'Enter') handleSelectChat(ws, chat.id); }}
                            className={`flex items-center gap-1.5 w-full pl-5 pr-2 py-1.5 text-[12px] rounded-r-md transition-colors text-left group cursor-pointer ${
                              isChatActive
                                ? 'bg-zinc-800 text-zinc-100'
                                : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'
                            }`}
                          >
                            <MessageSquare size={10} className="text-zinc-500 flex-shrink-0" />
                            <span className="truncate flex-1">{chat.title || 'Untitled'}</span>
                            <span className="text-[10px] text-zinc-600 flex-shrink-0 ml-1 tabular-nums">
                              {relativeTime(chat.updatedAt)}
                            </span>
                            <button
                              onClick={(e) => handleDeleteChat(e, ws, chat.id)}
                              className="p-0.5 text-zinc-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded flex-shrink-0"
                              title="Delete conversation"
                            >
                              <Trash2 size={9} />
                            </button>
                          </div>
                        );
                      })
                    )}
                  </div>
                )}
              </div>
            );
          })}

          {/* Empty projects state */}
          {workspaces.length === 0 && (
            <div className="px-3 py-6 text-[12px] text-zinc-600 italic text-center leading-relaxed">
              <Folder size={24} className="mx-auto mb-2 text-zinc-700" />
              No projects yet.
              <br />
              <button
                onClick={handleAddWorkspace}
                className="text-blue-400 hover:text-blue-300 mt-1.5 transition-colors"
              >
                + Add your first folder
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ═══════ Settings footer ═══════ */}
      <div className="border-t border-zinc-800">
        <button
          onClick={onOpenSettings}
          className="flex items-center gap-2.5 w-full px-5 py-2 text-[13px] text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
        >
          <Settings size={15} className="text-zinc-500 flex-shrink-0" />
          <span>Settings</span>
        </button>
      </div>

      {/* ═══════ Fallback modal — only shown when native folder picker is unavailable ═══════ */}
      {showAddWs && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          onClick={() => setShowAddWs(false)}
        >
          <div
            className="rounded-xl p-6 w-[420px] bg-zinc-900 border border-zinc-700 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-4">
              <FolderOpen size={18} className="text-blue-400" />
              <h3 className="text-[15px] font-semibold text-zinc-100">Add Project Folder</h3>
            </div>

            <label className="block text-[11px] text-zinc-400 mb-1.5 font-semibold uppercase tracking-wider">
              Folder Path
            </label>
            <input
              type="text"
              value={newWsPath}
              onChange={(e) => setNewWsPath(e.target.value)}
              placeholder="e.g. D:\MyProject\my-app"
              className="w-full px-3 py-2 text-[13px] rounded-lg mb-4 outline-none bg-zinc-950 border border-zinc-700 text-zinc-100 placeholder:text-zinc-600 focus:border-blue-500/50 transition-colors"
              autoFocus
              onKeyDown={async (e) => {
                if (e.key === 'Enter' && newWsPath.trim()) {
                  try {
                    await addWorkspace(newWsPath.trim());
                    setNewWsPath(''); setShowAddWs(false);
                    await loadWorkspaces();
                  } catch (err) { alert(`Failed: ${err}`); }
                }
              }}
            />

            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setNewWsPath(''); setShowAddWs(false); }}
                className="px-4 py-1.5 text-[12px] text-zinc-400 hover:text-zinc-200 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={async () => {
                  if (!newWsPath.trim()) return;
                  try {
                    await addWorkspace(newWsPath.trim());
                    setNewWsPath(''); setShowAddWs(false);
                    await loadWorkspaces();
                  } catch (e) { alert(`Failed: ${e}`); }
                }}
                disabled={!newWsPath.trim()}
                className="px-4 py-1.5 text-[12px] font-semibold text-white rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-40 transition-colors"
              >
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
