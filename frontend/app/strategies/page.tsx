'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategiesApi, Strategy } from '@/lib/api/strategies';
import StrategyList from '@/components/StrategyList';
import StrategyDetailModal from '@/components/StrategyDetailModal';
import { useState } from 'react';

export default function StrategiesPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null);
  const [showHidden, setShowHidden] = useState(false);
  const queryClient = useQueryClient();

  const { data: strategies, isLoading, error, refetch } = useQuery({
    queryKey: ['strategies', showHidden],
    queryFn: () => strategiesApi.list(showHidden),
    staleTime: 30000,
    refetchOnMount: true,
  });

  const refreshMutation = useMutation({
    mutationFn: strategiesApi.refresh,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });

  const hideMutation = useMutation({
    mutationFn: strategiesApi.hide,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });

  const showMutation = useMutation({
    mutationFn: strategiesApi.show,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategies'] });
    },
  });

  const handleViewDetails = async (strategy: Strategy) => {
    if (!strategy.parameters) {
      try {
        const detailedStrategy = await strategiesApi.get(strategy.name);
        setSelectedStrategy(detailedStrategy);
      } catch {
        setSelectedStrategy(strategy);
      }
    } else {
      setSelectedStrategy(strategy);
    }
  };

  const handleToggleVisibility = (strategy: Strategy) => {
    if (strategy.is_hidden) {
      showMutation.mutate(strategy.name);
    } else {
      hideMutation.mutate(strategy.name);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-center items-center h-64">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-gray-600">Loading strategies...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-800 font-semibold mb-2">Error Loading Strategies</p>
            <p className="text-red-600 text-sm mb-4">
              {error instanceof Error ? error.message : 'An unexpected error occurred'}
            </p>
            <button
              onClick={() => refetch()}
              className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const visibleCount = strategies?.filter(s => !s.is_hidden).length ?? 0;
  const hiddenCount = strategies?.filter(s => s.is_hidden).length ?? 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">Trading Strategies</h1>
              <p className="text-gray-600 mt-1">
                {visibleCount} strategies available
                {hiddenCount > 0 && ` (${hiddenCount} hidden)`}
              </p>
            </div>
            <div className="flex items-center gap-3">
              {/* Show Hidden Toggle */}
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={showHidden}
                  onChange={(e) => setShowHidden(e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                Show hidden
              </label>
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="bg-green-600 text-white px-6 py-2.5 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium flex items-center gap-2"
              >
                {refreshMutation.isPending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                    Refreshing...
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Refresh
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Strategy List */}
        <StrategyList
          strategies={strategies || []}
          showHidden={showHidden}
          onViewDetails={handleViewDetails}
          onToggleVisibility={handleToggleVisibility}
          isToggling={hideMutation.isPending || showMutation.isPending}
        />
      </div>

      {/* Strategy Detail Modal */}
      <StrategyDetailModal
        strategy={selectedStrategy}
        onClose={() => setSelectedStrategy(null)}
      />
    </div>
  );
}
