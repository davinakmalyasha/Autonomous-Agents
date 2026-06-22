import { FolderOpen } from 'lucide-react';

interface Props {
  isOpen: boolean;
  value: string;
  onChange: (val: string) => void;
  onClose: () => void;
  onSubmit: () => void;
}

export default function SidebarAddFolderModal({ isOpen, value, onChange, onClose, onSubmit }: Props) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="rounded-xl p-6 w-[420px] bg-zinc-900 border border-zinc-700 shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 mb-4">
          <FolderOpen size={18} className="text-blue-400" />
          <h3 className="text-[15px] font-semibold text-zinc-100 font-bold">Add Project Folder</h3>
        </div>
        <label className="block text-[11px] text-zinc-500 mb-1.5 font-bold uppercase tracking-wider">Folder Path</label>
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="e.g. D:\MyProject\my-app"
          className="w-full px-3 py-2 text-[13px] rounded-lg mb-4 outline-none bg-zinc-950 border border-zinc-750 text-zinc-100 placeholder:text-zinc-650 focus:border-blue-500/50 transition-colors"
          autoFocus
          onKeyDown={(e) => {
            if (e.key === 'Enter' && value.trim()) {
              onSubmit();
            }
          }}
        />
        <div className="flex justify-end gap-2">
          <button onClick={onClose} className="px-4 py-1.5 text-[12px] text-zinc-400 hover:text-zinc-200 rounded-lg transition-colors">Cancel</button>
          <button onClick={onSubmit} disabled={!value.trim()} className="px-4 py-1.5 text-[12px] font-bold text-white rounded-lg bg-blue-600 hover:bg-blue-550 disabled:opacity-40 transition-colors">Add</button>
        </div>
      </div>
    </div>
  );
}
