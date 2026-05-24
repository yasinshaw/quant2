'use client';

import { Strategy } from '@/lib/api/strategies';
import StrategyCard from './StrategyCard';

interface Props {
  strategies: Strategy[];
  showHidden: boolean;
  onViewDetails: (strategy: Strategy) => void;
  onToggleVisibility: (strategy: Strategy) => void;
  isToggling: boolean;
}

export default function StrategyList({ strategies, showHidden, onViewDetails, onToggleVisibility, isToggling }: Props) {
  if (strategies.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600 text-lg">No strategies found.</p>
        <p className="text-gray-500 text-sm mt-2">
          Click the Refresh button to load strategies from the backend.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 items-stretch">
      {strategies.map((strategy) => (
        <StrategyCard
          key={strategy.name}
          strategy={strategy}
          showHidden={showHidden}
          onViewDetails={onViewDetails}
          onToggleVisibility={onToggleVisibility}
          isToggling={isToggling}
        />
      ))}
    </div>
  );
}
