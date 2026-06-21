import React from 'react';
import type { TokenUsage } from '../../types';

interface EfficiencyInsightsProps {
  tokenUsage: TokenUsage;
}

const AGENT_MAPPING = [
  { keys: ['dev', 'coder'], name: 'developer' },
  { keys: ['ba'], name: 'planning (ba)' },
  { keys: ['sa'], name: 'architecture (sa)' },
  { keys: ['tester', 'qa'], name: 'tester (qa)' },
  { keys: ['devops'], name: 'devops' },
  { keys: ['supervisor', 'director'], name: 'supervisor' },
  { keys: ['analytics'], name: 'analytics' }
];

export function EfficiencyInsights({ tokenUsage }: EfficiencyInsightsProps) {
  const { calls, total_cost: totalCost } = tokenUsage;
  if (calls.length < 2) return null;

  const agentCosts: Record<string, number> = {};
  const agentInputs: Record<string, number> = {};
  const agentHits: Record<string, number> = {};

  for (const call of calls) {
    const rawAgent = call.agent.toLowerCase();
    const match = AGENT_MAPPING.find(m => m.keys.some(k => rawAgent.includes(k)));
    const agent = match ? match.name : 'other';

    agentCosts[agent] = (agentCosts[agent] || 0) + call.cost;
    agentInputs[agent] = (agentInputs[agent] || 0) + call.input;
    agentHits[agent] = (agentHits[agent] || 0) + (call.cache_hits || 0);
  }

  let maxCostAgent = '', maxCost = 0;
  for (const [agent, cost] of Object.entries(agentCosts)) {
    if (cost > maxCost) { maxCost = cost; maxCostAgent = agent; }
  }

  let minRatioAgent = '', minRatio = 100;
  for (const [agent, input] of Object.entries(agentInputs)) {
    if (input > 1000) {
      const ratio = ((agentHits[agent] || 0) / input) * 100;
      if (ratio < minRatio) { minRatio = ratio; minRatioAgent = agent; }
    }
  }

  const costPercentage = totalCost > 0 ? (maxCost / totalCost) * 100 : 0;

  return (
    <div className="p-3 rounded-lg border text-xs space-y-2.5"
         style={{ backgroundColor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}>
      <div className="font-semibold uppercase tracking-wider flex items-center gap-1.5" style={{ color: 'var(--accent)' }}>
        <span>📊</span> Cost & Cache Efficiency Insights
      </div>
      <div className="space-y-2">
        {maxCost > 0 && (
          <div className="flex gap-2 items-start">
            <span className="text-amber-500">⚠️</span>
            <div>
              <span className="font-semibold">Primary Cost Driver: </span>
              <span className="opacity-90">
                The <strong className="capitalize text-zinc-100">{maxCostAgent}</strong> agent is responsible for{' '}
                <strong className="text-amber-400">{costPercentage.toFixed(0)}%</strong> of the total run cost (${maxCost.toFixed(5)}).
              </span>
            </div>
          </div>
        )}
        {minRatioAgent && minRatio < 60 && (
          <div className="flex gap-2 items-start">
            <span className="text-blue-400">💡</span>
            <div>
              <span className="font-semibold">Cache Miss Inefficiency: </span>
              <span className="opacity-90">
                <strong className="capitalize text-zinc-100">{minRatioAgent}</strong> has a low prompt cache hit rate of{' '}
                <strong className="text-red-400">{minRatio.toFixed(1)}%</strong>.
                {minRatioAgent === 'developer' && ' Use partial reads (`offset`/`limit`) or `view_signatures` first to reuse prompt prefixes.'}
                {minRatioAgent === 'tester (qa)' && ' Traceback logs are too large. Log compactors/cleaners are critical.'}
              </span>
            </div>
          </div>
        )}
        {(!minRatioAgent || minRatio >= 60) && maxCost > 0 && (
          <div className="flex gap-2 items-start">
            <span className="text-emerald-400">✓</span>
            <div>
              <span className="font-semibold text-emerald-400">Optimal Cache Performance:</span>{' '}
              <span className="opacity-90">All agents are utilizing DeepSeek KV cache hits efficiently (&gt;60% hit ratio). Prefix reuse is working perfectly.</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
