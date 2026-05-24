'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { dataApi, Dataset } from '@/lib/api/data';
import ConfirmDialog from './ConfirmDialog';
import RenameDatasetDialog from './RenameDatasetDialog';
import { Trash2, Edit2 } from 'lucide-react';

interface Props {
  onSymbolSelect: (symbol: string, interval: string, datasetId?: number) => void;
  selectedDatasetId?: number;
}

export default function DownloadedDataSidebar({
  onSymbolSelect,
  selectedDatasetId,
}: Props) {
  // Fetch datasets
  const {
    data: datasets,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ['datasets'],
    queryFn: () => dataApi.getDatasets(),
    staleTime: 30000, // 30 seconds cache
    refetchOnWindowFocus: true,
  });

  const queryClient = useQueryClient();

  // Delete dialog state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedDeletion, setSelectedDeletion] = useState<Dataset | null>(null);

  // Rename dialog state
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [selectedRename, setSelectedRename] = useState<Dataset | null>(null);

  // Format ISO date string to YYYY-MM-DD
  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toISOString().split('T')[0];
  };

  // Format number with locale separators
  const formatCount = (count: number): string => {
    return count.toLocaleString();
  };

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (datasetId: number) => dataApi.deleteDataset(datasetId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: (error) => {
      // Error is already handled by toast notifications
    },
  });

  // Rename mutation
  const renameMutation = useMutation({
    mutationFn: ({ datasetId, name }: { datasetId: number; name: string }) =>
      dataApi.renameDataset(datasetId, name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: (error) => {
      // Error is already handled by toast notifications
    },
  });

  // Delete handlers
  const handleDeleteClick = (dataset: Dataset) => {
    setSelectedDeletion(dataset);
    setDeleteDialogOpen(true);
  };

  const handleConfirmDelete = () => {
    if (selectedDeletion) {
      deleteMutation.mutate(selectedDeletion.id);
      setDeleteDialogOpen(false);
      setSelectedDeletion(null);
    }
  };

  const handleCancelDelete = () => {
    setDeleteDialogOpen(false);
    setSelectedDeletion(null);
  };

  // Rename handlers
  const handleRenameClick = (dataset: Dataset) => {
    setSelectedRename(dataset);
    setRenameDialogOpen(true);
  };

  const handleConfirmRename = (name: string) => {
    if (selectedRename) {
      renameMutation.mutate({
        datasetId: selectedRename.id,
        name,
      });
      setRenameDialogOpen(false);
      setSelectedRename(null);
    }
  };

  const handleCancelRename = () => {
    setRenameDialogOpen(false);
    setSelectedRename(null);
  };

  // Loading state - skeleton screen
  if (isLoading) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto p-4">
        <h2 className="text-lg font-semibold mb-4">已下载数据</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="animate-pulse">
              <div className="h-20 bg-gray-200 rounded"></div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto p-4">
        <h2 className="text-lg font-semibold mb-4">已下载数据</h2>
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800 text-sm mb-3">
            加载失败: {error instanceof Error ? error.message : '未知错误'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 transition-colors"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  // Empty state
  if (!datasets || datasets.length === 0) {
    return (
      <div className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto p-4">
        <h2 className="text-lg font-semibold mb-4">已下载数据</h2>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          <p className="text-gray-600 mb-2">暂无已下载数据</p>
          <p className="text-gray-400 text-sm">请先下载历史数据</p>
        </div>
      </div>
    );
  }

  // Normal rendering - flat list of datasets
  return (
    <div
      className="w-[300px] h-screen sticky top-0 bg-white border-r border-gray-200 overflow-y-auto"
      data-testid="downloaded-sidebar"
    >
      <div className="p-4">
        <h2 className="text-lg font-semibold mb-4">已下载数据</h2>

        <div className="space-y-3">
          {datasets.map((dataset: Dataset) => {
            const isSelected = selectedDatasetId === dataset.id;

            return (
              <div
                key={dataset.id}
                className={`border rounded-lg overflow-hidden transition-colors ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
              >
                <button
                  onClick={() => onSymbolSelect(dataset.symbol, dataset.interval, dataset.id)}
                  aria-pressed={isSelected}
                  data-testid="dataset-item"
                  className="w-full px-4 py-3 text-left"
                >
                  {/* Dataset name */}
                  <div className="font-medium text-gray-900 mb-2">
                    {dataset.name}
                  </div>

                  {/* Symbol and interval */}
                  <div className="text-sm text-gray-600 mb-1">
                    {dataset.symbol} · {dataset.interval}
                  </div>

                  {/* Date range */}
                  <div className="text-xs text-gray-500 mb-1">
                    {formatDate(dataset.start_time)} ~ {formatDate(dataset.end_time)}
                  </div>

                  {/* Candle count and actions */}
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500">
                      {formatCount(dataset.candle_count)} 条
                    </span>
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRenameClick(dataset);
                        }}
                        className="p-1 hover:bg-gray-100 rounded transition-colors"
                        aria-label={`重命名 ${dataset.name}`}
                        disabled={renameMutation.isPending}
                      >
                        <Edit2 className="w-4 h-4 text-gray-600" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteClick(dataset);
                        }}
                        className="p-1 hover:bg-red-100 rounded transition-colors"
                        aria-label={`删除 ${dataset.name}`}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="w-4 h-4 text-red-600" />
                      </button>
                    </div>
                  </div>
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={deleteDialogOpen}
        onConfirm={handleConfirmDelete}
        onCancel={handleCancelDelete}
        title="确认删除"
        message={`确定要删除数据集 "${selectedDeletion?.name}" 吗？此操作不可恢复。`}
        details={
          selectedDeletion
            ? {
                count: selectedDeletion.candle_count,
                startTime: selectedDeletion.start_time,
                endTime: selectedDeletion.end_time,
              }
            : undefined
        }
        confirmText="删除"
        cancelText="取消"
        variant="danger"
      />

      {/* Rename dialog */}
      <RenameDatasetDialog
        dataset={selectedRename}
        onConfirm={handleConfirmRename}
        onCancel={handleCancelRename}
      />
    </div>
  );
}
