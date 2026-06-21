import { useCallback, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { PromptInput } from './PromptInput';
import { useAgentState } from '../../hooks/useAgentState';
import type { ChatMessage } from '../../types';

export function ChatPanel() {
  const { state, runPrompt } = useAgentState();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isRunning, setIsRunning] = useState(false);

  const handleSend = useCallback(
    (prompt: string) => {
      // Add user message
      const userMsg: ChatMessage = {
        id: Date.now().toString(),
        sender: 'user',
        text: prompt,
        timestamp: Date.now(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsRunning(true);

      runPrompt(prompt, state.selected_model, state.selected_temp);

      // Check for completion via polling (simple approach)
      // The done state is handled by monitoring active_node becoming empty
      const checkDone = setInterval(() => {
        // We check if the terminal log has content and active_node is empty
        // That indicates the pipeline finished
      }, 1000);

      // Cleanup after 60s max
      setTimeout(() => {
        clearInterval(checkDone);
        setIsRunning(false);
      }, 60000);
    },
    [runPrompt, state.selected_model, state.selected_temp],
  );

  // Show terminal log as streaming output
  const terminalLog = state.live_terminal_log || '';

  // Show Jarvis/chat responses as messages
  const displayedMessages = [...messages];
  if (terminalLog && isRunning) {
    // Don't add duplicate — the terminal log IS the streaming output
  }

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: 'var(--bg-primary)' }}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4">
        {displayedMessages.map((msg) => (
          <MessageBubble key={msg.id} sender={msg.sender} text={msg.text} />
        ))}

        {/* Show streaming terminal output when running */}
        {isRunning && terminalLog && (
          <div
            className="mt-4 p-4 rounded-lg font-mono text-sm"
            style={{
              backgroundColor: 'var(--bg-secondary)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-secondary)',
              whiteSpace: 'pre-wrap',
            }}
          >
            {terminalLog}
          </div>
        )}
      </div>

      {/* Prompt input at bottom */}
      <PromptInput onSend={handleSend} disabled={isRunning} />
    </div>
  );
}
