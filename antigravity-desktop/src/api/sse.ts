import { API_BASE } from './client';

export type SSEEventHandler = (event: string, data: unknown) => void;

/**
 * Opens an SSE connection to POST /api/run with the given prompt.
 * Calls onEvent for each SSE event received.
 * Returns an abort function to cancel the stream.
 */
export function streamRun(
  prompt: string,
  model: string,
  temperature: number,
  onEvent: SSEEventHandler,
): AbortController {
  const controller = new AbortController();

  const body = JSON.stringify({
    prompt,
    model,
    temperature,
  });

  fetch(`${API_BASE}/api/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const text = await res.text();
        onEvent('error', { error: `API ${res.status}: ${text}` });
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onEvent('error', { error: 'No response body' });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE frames: "event: <name>\ndata: <json>\n\n"
        const parts = buffer.split('\n\n');
        buffer = parts.pop() || '';

        for (const part of parts) {
          const lines = part.split('\n');
          let eventName = '';
          let dataStr = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventName = line.slice(7);
            } else if (line.startsWith('data: ')) {
              dataStr = line.slice(6);
            }
          }

          if (eventName && dataStr) {
            try {
              const data = JSON.parse(dataStr);
              onEvent(eventName, data);
            } catch {
              // Skip malformed JSON
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        onEvent('error', { error: err.message });
      }
    });

  return controller;
}
