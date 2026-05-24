'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { historyApi, HistoryQueryParams } from '@/lib/api/history';
import { strategiesApi } from '@/lib/api/strategies';
import { dataApi, ClearHistoryResponse } from '@/lib/api/data';
import HistoryTabs from '@/components/HistoryTabs';
import HistoryFilters from '@/components/HistoryFilters';
import BacktestHistoryTable from '@/components/BacktestHistoryTable';
import OptimizationHistoryTable from '@/components/OptimizationHistoryTable';
import Pagination from '@/components/Pagination';
import ConfirmDialog from '@/components/ConfirmDialog';
import { toast } from '@/lib/toast';

const DEFAULT_PAGE_SIZE = 10;

// Common trading symbols (can be fetched from API later if needed)
const COMMON_SYMBOLS = [
  'BTCUSDT',
  'ETHUSDT',
  'BNBUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'XRPUSDT',
  'DOTUSDT',
  'UNIUSDT',
  'LTCUSDT',
  'LINKUSDT',
];

export default function HistoryPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  // State management
  const [activeTab, setActiveTab] = useState<'backtest' | 'optimization'>('backtest');
  const [filters, setFilters] = useState<HistoryQueryParams>({
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  });
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [showClearAllDialog, setShowClearAllDialog] = useState(false);
  const [showClearBacktestDialog, setShowClearBacktestDialog] = useState(false);
  const [showClearOptimizationDialog, setShowClearOptimizationDialog] = useState(false);

  // Fetch strategies for filter dropdown
  const { data: strategies } = useQuery({
    queryKey: ['strategies'],
    queryFn: () => strategiesApi.list(),
    staleTime: 60000, // 1 minute
  });

  // Fetch backtest history
  const {
    data: backtestData,
    isLoading: isLoadingBacktest,
    error: backtestError,
    refetch: refetchBacktest,
  } = useQuery({
    queryKey: ['backtest-history', filters],
    queryFn: () => historyApi.getBacktestHistory(filters),
    enabled: activeTab === 'backtest',
    staleTime: 30000, // 30 seconds
    placeholderData: (previousData) => previousData, // keepPreviousData equivalent
  });

  // Fetch optimization history
  const {
    data: optimizationData,
    isLoading: isLoadingOptimization,
    error: optimizationError,
    refetch: refetchOptimization,
  } = useQuery({
    queryKey: ['optimization-history', filters],
    queryFn: () => historyApi.getOptimizationHistory(filters),
    enabled: activeTab === 'optimization',
    staleTime: 30000, // 30 seconds
    placeholderData: (previousData) => previousData, // keepPreviousData equivalent
  });

  // Delete backtest job mutation
  const deleteBacktestMutation = useMutation({
    mutationFn: historyApi.deleteBacktestJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
      setDeleteError(null);
    },
    onError: (error: any) => {
      setDeleteError(error?.response?.data?.detail || 'Failed to delete backtest job');
    },
  });

  // Delete optimization job mutation
  const deleteOptimizationMutation = useMutation({
    mutationFn: historyApi.deleteOptimizationJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['optimization-history'] });
      setDeleteError(null);
    },
    onError: (error: any) => {
      setDeleteError(error?.response?.data?.detail || 'Failed to delete optimization job');
    },
  });

  // Toggle favorite mutation with optimistic update
  const toggleFavoriteMutation = useMutation({
    mutationFn: historyApi.toggleBacktestFavorite,
    onMutate: async (jobId) => {
      await queryClient.cancelQueries({ queryKey: ['backtest-history'] });
      const previous = queryClient.getQueryData(['backtest-history', filters]);
      queryClient.setQueryData(['backtest-history', filters], (old: any) => {
        if (!old) return old;
        return {
          ...old,
          items: old.items.map((item: any) =>
            item.job_id === jobId
              ? { ...item, is_favorite: !item.is_favorite }
              : item
          ),
        };
      });
      return { previous };
    },
    onError: (_err, _jobId, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['backtest-history', filters], context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
    },
  });

  // Clear all history mutation
  const clearAllHistoryMutation = useMutation({
    mutationFn: () => dataApi.clearAllHistory(),
    onSuccess: (data: ClearHistoryResponse) => {
      toast.success(`已清空所有历史记录（${data.total_deleted} 条）`);
      queryClient.invalidateQueries({ queryKey: ['backtest-history'] });
      queryClient.invalidateQueries({ queryKey: ['optimization-history'] });
      setShowClearAllDialog(false);
    },
    onError: (error: any) => {
      const errorMessage = error?.response?.data?.detail || '清空失败';
      toast.error(errorMessage);
    },
  });

  // Handle tab change
  const handleTabChange = (tab: 'backtest' | 'optimization') => {
    setActiveTab(tab);
    setFilters({ ...filters, page: 1 }); // Reset to first page when switching tabs
    setDeleteError(null);
  };

  // Handle filter change
  const handleFilterChange = (newFilters: HistoryQueryParams) => {
    setFilters({ ...newFilters, page: 1 }); // Reset to first page when filters change
    setDeleteError(null);
  };

  // Handle clear filters
  const handleClearFilters = () => {
    setFilters({ page: 1, page_size: DEFAULT_PAGE_SIZE });
    setDeleteError(null);
  };

  // Handle page change
  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page });
    setDeleteError(null);
  };

  // Handle delete backtest job
  const handleDeleteBacktest = (jobId: number) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this backtest job? This action cannot be undone.'
    );

    if (confirmed) {
      deleteBacktestMutation.mutate(jobId);
    }
  };

  // Handle delete optimization job
  const handleDeleteOptimization = (jobId: number) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this optimization job? This action cannot be undone.'
    );

    if (confirmed) {
      deleteOptimizationMutation.mutate(jobId);
    }
  };

  // Handle view backtest details
  const handleViewBacktest = (jobId: number) => {
    router.push(`/results/${jobId}`);
  };

  // Handle view optimization details
  const handleViewOptimization = (jobId: number) => {
    router.push(`/optimization-results/${jobId}`);
  };

  // Extract data based on active tab
  const isLoading = activeTab === 'backtest' ? isLoadingBacktest : isLoadingOptimization;
  const error = activeTab === 'backtest' ? backtestError : optimizationError;
  const refetch = activeTab === 'backtest' ? refetchBacktest : refetchOptimization;

  // Extract strategy names for filter
  const strategyNames = strategies?.map((s) => s.name) || [];

  // Render loading state
  if (isLoading && !backtestData && !optimizationData) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-heading font-bold text-slate-900 dark:text-slate-100">
            History
          </h1>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-12 border border-slate-200 dark:border-slate-700">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
          <p className="text-center text-slate-500 dark:text-slate-400 mt-4">Loading history...</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error && !backtestData && !optimizationData) {
    return (
      <div className="container mx-auto px-4 py-8 max-w-7xl">
        <div className="mb-8">
          <h1 className="text-3xl font-heading font-bold text-slate-900 dark:text-slate-100">
            History
          </h1>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-md p-12 border border-slate-200 dark:border-slate-700">
          <div className="text-center">
            <p className="text-red-600 dark:text-red-400 mb-4">
              Failed to load history data. Please try again.
            </p>
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 dark:bg-primary-500 dark:hover:bg-primary-600 text-white rounded-lg transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      {/* Page Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-heading font-bold text-slate-900 dark:text-slate-100">
            History
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            View and manage your backtest and optimization history
          </p>
        </div>
        <button
          onClick={() => setShowClearAllDialog(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 transition-colors"
        >
          清空所有历史
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="mb-6">
        <HistoryTabs activeTab={activeTab} onTabChange={handleTabChange} />
      </div>

      {/* Filters */}
      <div className="mb-6">
        <HistoryFilters
          filters={filters}
          onFilterChange={handleFilterChange}
          onClear={handleClearFilters}
          strategies={strategyNames}
          symbols={COMMON_SYMBOLS}
        />
      </div>

      {/* Delete Error Message */}
      {deleteError && (
        <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-400">{deleteError}</p>
        </div>
      )}

      {/* Content */}
      <div className="mb-6">
        {activeTab === 'backtest' ? (
          <BacktestHistoryTable
            data={backtestData?.items || []}
            onDelete={handleDeleteBacktest}
            onView={handleViewBacktest}
            onToggleFavorite={(jobId) => toggleFavoriteMutation.mutate(jobId)}
          />
        ) : (
          <OptimizationHistoryTable
            data={optimizationData?.items || []}
            onDelete={handleDeleteOptimization}
            onView={handleViewOptimization}
          />
        )}
      </div>

      {/* Pagination */}
      {activeTab === 'backtest' && backtestData && (
        <Pagination
          currentPage={backtestData.page}
          totalPages={backtestData.total_pages}
          onPageChange={handlePageChange}
        />
      )}
      {activeTab === 'optimization' && optimizationData && (
        <Pagination
          currentPage={optimizationData.page}
          totalPages={optimizationData.total_pages}
          onPageChange={handlePageChange}
        />
      )}

      {/* Clear All History Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showClearAllDialog}
        onConfirm={() => clearAllHistoryMutation.mutate()}
        onCancel={() => setShowClearAllDialog(false)}
        title="确认清空所有历史记录"
        message="此操作将清空所有回测和调优历史记录，包括所有回测任务、回测结果、交易记录、调优任务和调优结果。此操作不可撤销，请确认是否继续。"
        confirmText="确认清空"
        cancelText="取消"
        variant="danger"
      />
    </div>
  );
}
