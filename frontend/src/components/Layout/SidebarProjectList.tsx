import { Folder, ChevronRight, ChevronDown, Plus, Trash2, MessageSquare } from 'lucide-react';
import type { WorkspaceInfo, ChatSummary } from '../../types';

interface Props {
  workspaces: WorkspaceInfo[];
  expandedWs: Set<string>;
  chatMap: Record<string, ChatSummary[]>;
  activeWorkspaceId: string | null;
  activeChatId: string | null;
  toggleWs: (ws: WorkspaceInfo) => void;
  handleCreateChat: (ws: WorkspaceInfo) => void;
  removeWorkspace: (id: string) => Promise<any>;
  loadWorkspaces: () => Promise<any>;
  handleDeleteChat: (e: React.MouseEvent, ws: WorkspaceInfo, chatId: string) => void;
  handleSelectChat: (ws: WorkspaceInfo, chatId: string) => void;
  relativeTime: (iso: string) => string;
  handleAddWorkspace: () => void;
}

export default function SidebarProjectList({
  workspaces, expandedWs, chatMap, activeWorkspaceId, activeChatId,
  toggleWs, handleCreateChat, removeWorkspace, loadWorkspaces,
  handleDeleteChat, handleSelectChat, relativeTime, handleAddWorkspace
}: Props) {
  return (
    <div className="flex-1 overflow-y-auto" style={{ paddingLeft: '6px', paddingRight: '8px' }}>
      {workspaces.map((ws) => {
        const isExpanded = expandedWs.has(ws.id);
        const isActive = ws.id === activeWorkspaceId;
        const chats = chatMap[ws.id] || [];

        return (
          <div key={ws.id} className="mb-0.5">
            <div className="flex items-center gap-0 group">
              <button
                onClick={() => toggleWs(ws)}
                className={`flex items-center gap-1.5 flex-1 text-[12px] rounded-md transition-colors text-left min-w-0 ${
                  isActive
                    ? 'text-zinc-200 font-semibold hover:bg-zinc-800/50'
                    : 'text-zinc-400 hover:bg-zinc-800/50 hover:text-zinc-200'
                }`}
                style={{ padding: '6px 8px' }}
              >
                {isExpanded ? (
                  <ChevronDown size={12} className="text-zinc-500 flex-shrink-0" />
                ) : (
                  <ChevronRight size={12} className="text-zinc-500 flex-shrink-0" />
                )}
                <Folder size={13} className={`${isActive ? 'text-zinc-300' : 'text-zinc-500'} flex-shrink-0`} />
                <span className="truncate font-medium">{ws.name}</span>
                <span className="text-[10px] text-zinc-600 ml-auto flex-shrink-0">{chats.length}</span>
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); handleCreateChat(ws); }}
                className="p-0.5 text-zinc-650 hover:text-zinc-350 opacity-0 group-hover:opacity-100 transition-all rounded"
                title="New conversation"
              >
                <Plus size={11} />
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); removeWorkspace(ws.id).then(loadWorkspaces); }}
                className="p-0.5 text-zinc-650 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded"
                title="Remove project"
              >
                <Trash2 size={10} />
              </button>
            </div>

            {isExpanded && (
              <div style={{ marginLeft: '26px', borderLeft: '1px solid rgba(63, 63, 70, 0.4)' }}>
                {chats.length === 0 ? (
                  <div
                    className="text-[11px] text-zinc-600 italic cursor-pointer hover:text-zinc-450 transition-colors"
                    style={{ padding: '8px 16px' }}
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
                        className={`flex items-center gap-1.5 w-full text-[12px] rounded-r-md transition-colors text-left group cursor-pointer ${
                          isChatActive ? 'bg-zinc-800 text-zinc-100' : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'
                        }`}
                        style={{ paddingLeft: '22px', paddingRight: '8px', paddingTop: '7px', paddingBottom: '7px' }}
                      >
                        <MessageSquare size={10} className="text-zinc-550 flex-shrink-0" />
                        <span className="truncate flex-1">{chat.title || 'Untitled'}</span>
                        <span className="text-[10px] text-zinc-650 flex-shrink-0 ml-1 tabular-nums">
                          {relativeTime(chat.updatedAt)}
                        </span>
                        <button
                          onClick={(e) => handleDeleteChat(e, ws, chat.id)}
                          className="p-0.5 text-zinc-650 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all rounded flex-shrink-0"
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

      {workspaces.length === 0 && (
        <div className="px-3 py-6 text-[12px] text-zinc-600 italic text-center leading-relaxed">
          <Folder size={24} className="mx-auto mb-2 text-zinc-700" />
          No projects yet.
          <br />
          <button onClick={handleAddWorkspace} className="text-blue-400 hover:text-blue-300 mt-1.5 transition-colors">
            + Add your first folder
          </button>
        </div>
      )}
    </div>
  );
}
