import { useEffect, useRef } from 'react';

interface StreamingOutputProps {
  text: string;
}

export function StreamingOutput({ text }: StreamingOutputProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [text]);

  return (
    <div
      className="flex-1 overflow-y-auto p-4 font-mono text-sm leading-relaxed"
      style={{
        backgroundColor: 'var(--bg-primary)',
        color: 'var(--text-secondary)',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
      }}
    >
      {text || (
        <span className="opacity-40 italic">
          Waiting for agent output...
        </span>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
