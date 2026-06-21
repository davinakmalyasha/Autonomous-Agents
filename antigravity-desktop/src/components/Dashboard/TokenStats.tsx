import React from 'react';
import type { TokenUsage } from '../../types';
import { TokenSummary } from './TokenSummary';
import { EfficiencyInsights } from './EfficiencyInsights';
import { CallList } from './CallList';

interface TokenStatsProps {
  tokenUsage: TokenUsage;
}

export function TokenStats({ tokenUsage }: TokenStatsProps) {
  if (!tokenUsage || !tokenUsage.calls || tokenUsage.calls.length === 0) {
    return (
      <div
        className="p-4 rounded-lg text-xs italic"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          border: '1px solid var(--border-color)',
          color: 'var(--text-secondary)',
        }}
      >
        No token usage yet. Start the pipeline to analyze costs.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 1. Header & Summary Grid */}
      <TokenSummary tokenUsage={tokenUsage} />

      {/* 2. Efficiency & Caching Insights */}
      <EfficiencyInsights tokenUsage={tokenUsage} />

      {/* 3. Call Log Details */}
      <CallList calls={tokenUsage.calls} />
    </div>
  );
}
