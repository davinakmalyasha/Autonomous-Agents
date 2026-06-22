import { useRef, useEffect } from 'react';
import { Zap } from 'lucide-react';
import type { ChatMessage } from '../../types';
import MessageBubble from './MessageBubble';

interface Props {
  messages: ChatMessage[];
  hasActiveChat: boolean;
}

export default function MessageStream({ messages, hasActiveChat }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const isAtBottomRef = useRef(true);
  const lastScrollHeightRef = useRef(0);

  useEffect(() => {
    if (scrollRef.current) {
      lastScrollHeightRef.current = scrollRef.current.scrollHeight;
    }
  }, []);

  useEffect(() => {
    if (!scrollRef.current || !isAtBottomRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  useEffect(() => {
    if (!contentRef.current) return;
    const observer = new ResizeObserver(() => {
      if (isAtBottomRef.current && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      }
    });
    observer.observe(contentRef.current);
    return () => observer.disconnect();
  }, [messages, hasActiveChat]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const el = scrollRef.current;
    const wasAtBottom = isAtBottomRef.current;
    const heightChanged = el.scrollHeight !== lastScrollHeightRef.current;
    let bottom = el.scrollHeight - el.clientHeight <= el.scrollTop + 60;
    if (heightChanged && wasAtBottom) bottom = true;
    lastScrollHeightRef.current = el.scrollHeight;
    isAtBottomRef.current = bottom;
  };

  const isEmpty = !hasActiveChat && messages.length <= 1;

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto"
      style={{ paddingLeft: '24px', paddingRight: '24px', paddingTop: '16px', paddingBottom: '16px' }}
    >
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center min-h-[220px] h-full text-center max-w-md mx-auto px-4 py-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-zinc-900 border border-zinc-800 mb-4 flex-shrink-0">
            <Zap size={22} className="text-yellow-400" />
          </div>
          <h2 className="text-md font-bold text-zinc-200 mb-1">VinCode Supervisor</h2>
          <p className="text-[12.5px] text-zinc-450 leading-relaxed mb-4">
            Supervisor + Developer multi-agent pipeline.
          </p>
          <div className="flex flex-col gap-1.5 text-left text-[11px] text-zinc-500 max-w-xs">
            <div>• Start typing below to consult the Supervisor</div>
            <div>• Developer agent uses file tools to read/write code</div>
          </div>
        </div>
      ) : (
        <div ref={contentRef} className="max-w-[810px] mx-auto" style={{ width: '100%' }}>
          {messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))}
        </div>
      )}
    </div>
  );
}
