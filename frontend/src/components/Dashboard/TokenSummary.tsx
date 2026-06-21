import React from 'react';
import type { TokenUsage } from '../../types';

interface TokenSummaryProps {
  tokenUsage: TokenUsage;
}

export function TokenSummary({ tokenUsage }: TokenSummaryProps) {
  const totalCost = tokenUsage.total_cost;
  const input = tokenUsage.total_input_tokens || 0;
  const output = tokenUsage.total_output_tokens || 0;
  const cacheHits = tokenUsage.total_cache_hit_tokens || 0;

  // Calculate Cache Hit Ratio
  const hitRatio = input > 0 ? (cacheHits / input) * 100 : 0;

  // Calculate Savings from Cache Hits
  let totalSavings = 0;
  for (const call of tokenUsage.calls) {
    const hits = call.cache_hits || 0;
    if (hits <= 0) continue;
    const model = call.model.toLowerCase();
    let savingsRate = 0.126; // Default to Flash savings rate: 0.14 - 0.014 = 0.126 per 1M
    if (model.includes('pro')) {
      savingsRate = 1.566; // Pro: 1.74 - 0.174 = 1.566 per 1M
    } else if (model.includes('reasoner') || model.includes('r1')) {
      savingsRate = 0.41;  // R1: 0.55 - 0.14 = 0.41 per 1M
    }
    totalSavings += (hits / 1000000) * savingsRate;
  }

  const savingsPct = (totalCost + totalSavings) > 0 ? (totalSavings / (totalCost + totalSavings)) * 100 : 0;

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
      {/* Total Cost Card */}
      <div className="p-3 rounded-lg border bg-zinc-900/50" style={{ borderColor: 'var(--border-color)' }}>
        <span className="text-xs uppercase tracking-wider font-semibold opacity-60">Total Burned</span>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-xl font-bold text-emerald-400">${totalCost.toFixed(5)}</span>
          <span className="text-[10px] opacity-50">USD</span>
        </div>
        <span className="text-[10px] opacity-50 mt-1 block">In: {input.toLocaleString()} | Out: {output.toLocaleString()}</span>
      </div>

      {/* Cache Hit Ratio Card */}
      <div className="p-3 rounded-lg border bg-zinc-900/50" style={{ borderColor: 'var(--border-color)' }}>
        <span className="text-xs uppercase tracking-wider font-semibold opacity-60">Cache Efficiency</span>
        <div className="mt-2">
          <span className="text-xl font-bold text-indigo-400">{hitRatio.toFixed(1)}%</span>
          <div className="w-full h-1.5 rounded-full mt-2 overflow-hidden bg-zinc-800">
            <div className="h-full rounded-full transition-all duration-500 bg-indigo-500" 
                 style={{ width: `${hitRatio}%` }} />
          </div>
        </div>
        <span className="text-[10px] opacity-50 mt-1 block">Cached: {cacheHits.toLocaleString()} tokens</span>
      </div>

      {/* Savings Card */}
      <div className="p-3 rounded-lg border bg-zinc-900/50" style={{ borderColor: 'var(--border-color)' }}>
        <span className="text-xs uppercase tracking-wider font-semibold opacity-60">Estimated Savings</span>
        <div className="mt-2 flex items-baseline gap-1">
          <span className="text-xl font-bold text-emerald-400">${totalSavings.toFixed(5)}</span>
          <span className="text-[10px] text-emerald-400 font-semibold">({savingsPct.toFixed(0)}% saved)</span>
        </div>
        <span className="text-[10px] opacity-50 mt-1 block">Via DeepSeek Context Caching</span>
      </div>
    </div>
  );
}
