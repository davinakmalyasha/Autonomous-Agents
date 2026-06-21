import React from 'react';
import type { TokenCall } from '../../types';

interface CallListProps {
  calls: TokenCall[];
}

export function CallList({ calls }: CallListProps) {
  if (!calls || calls.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="text-xs font-semibold uppercase tracking-wider opacity-60">
        Execution Call Log ({calls.length} calls)
      </div>
      
      <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
        {calls.slice().reverse().map((call, idx) => {
          const hits = call.cache_hits || 0;
          const misses = call.cache_misses || (call.input - hits);
          const totalInput = call.input;
          
          const hitPercent = totalInput > 0 ? (hits / totalInput) * 100 : 0;
          const cost = call.cost;

          return (
            <div
              key={idx}
              className="p-2.5 rounded-lg border text-xs flex flex-col gap-1.5 transition-all duration-200 hover:border-accent"
              style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <span className="px-1.5 py-0.5 rounded font-bold uppercase text-[10px]"
                        style={{ backgroundColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
                    {call.agent}
                  </span>
                  <span className="opacity-50 text-[10px]">{call.model}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-success">${cost.toFixed(6)}</span>
                  <span className="opacity-40 text-[9px]">{call.timestamp}</span>
                </div>
              </div>

              {call.where && (
                <div className="text-[10.5px] opacity-90 p-1.5 rounded border my-0.5 leading-normal"
                     style={{ backgroundColor: 'var(--bg-primary)', borderColor: 'var(--border-color)', color: 'var(--text-primary)' }}>
                  <span className="opacity-50 font-semibold uppercase text-[8px] block mb-0.5 tracking-wider">Action / Task Context</span>
                  {call.where}
                </div>
              )}
              
              {/* Cache Hit vs Miss Bar */}
              <div className="space-y-1">
                <div className="flex justify-between text-[9px] opacity-60">
                  <span>Cache Hits: {hits.toLocaleString()} ({hitPercent.toFixed(0)}%)</span>
                  <span>Miss: {misses.toLocaleString()} | Out: {call.output.toLocaleString()}</span>
                </div>
                <div className="w-full h-1 rounded overflow-hidden flex" style={{ backgroundColor: 'var(--border-color)' }}>
                  {hits > 0 && (
                    <div className="h-full" style={{ width: `${hitPercent}%`, backgroundColor: 'var(--success)' }} title={`Cached: ${hits}`} />
                  )}
                  {misses > 0 && (
                    <div className="h-full" style={{ width: `${100 - hitPercent}%`, backgroundColor: 'var(--text-secondary)' }} title={`Uncached: ${misses}`} />
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
