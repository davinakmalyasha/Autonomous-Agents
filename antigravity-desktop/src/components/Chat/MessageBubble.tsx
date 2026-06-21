interface MessageBubbleProps {
  sender: 'user' | 'jarvis' | 'agent';
  text: string;
}

function senderLabel(sender: string): string {
  switch (sender) {
    case 'user':
      return 'You';
    case 'jarvis':
      return 'Jarvis';
    default:
      return 'Agent';
  }
}

export function MessageBubble({ sender, text }: MessageBubbleProps) {
  const isUser = sender === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className="max-w-[80%] px-4 py-3 rounded-xl text-sm leading-relaxed"
        style={{
          backgroundColor: isUser ? 'var(--accent)' : 'var(--bg-secondary)',
          color: isUser ? '#fff' : 'var(--text-primary)',
          border: isUser ? 'none' : '1px solid var(--border-color)',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {!isUser && (
          <div
            className="text-xs font-semibold mb-1 uppercase tracking-wide"
            style={{ color: 'var(--accent)' }}
          >
            {senderLabel(sender)}
          </div>
        )}
        <div className="prose prose-sm max-w-none" style={{ color: 'inherit' }}>
          {text}
        </div>
      </div>
    </div>
  );
}
