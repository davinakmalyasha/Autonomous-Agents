import { useEffect, useRef, useCallback } from 'react';
import { useAgentContext } from '../context/AgentContext';
import { getState as fetchState, resetSession as resetApi } from '../api/client';
import { streamRun } from '../api/sse';
import type { AgentState } from '../types';

export function useAgentState() {
  const { state, dispatch } = useAgentContext();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Poll state every 1s
  const startPolling = useCallback(() => {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const raw = await fetchState();
        dispatch({ type: 'SET_STATE', payload: raw as unknown as Partial<AgentState> });
      } catch {
        // Backend not running — ignore
      }
    }, 1000);
  }, [dispatch]);

  const stopPolling = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  useEffect(() => {
    startPolling();
    return stopPolling;
  }, [startPolling, stopPolling]);

  // Run a prompt through the SSE pipeline
  const runPrompt = useCallback(
    (prompt: string, model: string, temperature: number) => {
      // Cancel any existing stream
      if (abortRef.current !== null) {
        abortRef.current.abort();
      }

      abortRef.current = streamRun(prompt, model, temperature, (event, data) => {
        if (event === 'state') {
          dispatch({ type: 'SET_STATE', payload: data as Partial<AgentState> });
        } else if (event === 'error') {
          dispatch({
            type: 'SET_ERROR',
            payload: (data as { error: string }).error,
          });
        }
        // 'done' event is handled implicitly — polling continues
      });
    },
    [dispatch],
  );

  // Reset session
  const resetSession = useCallback(async () => {
    try {
      await resetApi();
      dispatch({ type: 'RESET' });
    } catch {
      dispatch({ type: 'RESET' });
    }
  }, [dispatch]);

  return { state, runPrompt, resetSession };
}
