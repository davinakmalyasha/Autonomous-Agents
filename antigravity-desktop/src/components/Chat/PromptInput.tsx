import { useState, type FormEvent } from 'react';

interface PromptInputProps {
  onSend: (prompt: string) => void;
  disabled?: boolean;
}

export function PromptInput({ onSend, disabled }: PromptInputProps) {
  const [text, setText] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="border-t flex gap-3 p-4"
      style={{
        borderColor: 'var(--border-color)',
        backgroundColor: 'var(--bg-secondary)',
      }}
    >
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Start typing a prompt to see what our agents can do..."
        disabled={disabled}
        className="flex-1 px-4 py-3 rounded-lg text-sm outline-none transition-colors
                   disabled:opacity-50"
        style={{
          backgroundColor: 'var(--bg-primary)',
          color: 'var(--text-primary)',
          border: '1px solid var(--border-color)',
        }}
        onFocus={(e) => {
          e.target.style.borderColor = 'var(--accent)';
        }}
        onBlur={(e) => {
          e.target.style.borderColor = 'var(--border-color)';
        }}
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="px-6 py-3 rounded-lg text-sm font-semibold transition-all
                   disabled:opacity-40 disabled:cursor-not-allowed
                   hover:scale-[1.02] active:scale-[0.98]"
        style={{
          background: 'var(--accent-gradient)',
          color: '#fff',
        }}
      >
        Run ⚡
      </button>
    </form>
  );
}
