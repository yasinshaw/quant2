'use client';

import { useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';

interface ConfirmDialogProps {
  isOpen: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  title: string;
  message: string;
  details?: {
    count: number;
    startTime: string;
    endTime: string;
  };
  confirmText?: string;
  cancelText?: string;
  variant?: 'danger' | 'warning';
}

export default function ConfirmDialog({
  isOpen,
  onConfirm,
  onCancel,
  title,
  message,
  details,
  confirmText = '删除',
  cancelText = '取消',
  variant = 'danger',
}: ConfirmDialogProps) {
  // Handle ESC key press
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onCancel();
      }
    },
    [onCancel]
  );

  // Prevent body scroll when open and handle ESC key
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      // 禁用背景页面的所有交互
      document.body.style.pointerEvents = 'none';
      // 隐藏所有 Ant Design 下拉面板
      const style = document.createElement('style');
      style.id = 'confirm-dialog-override';
      style.textContent = `
        .ant-picker-dropdown,
        .ant-select-dropdown,
        .ant-dropdown {
          display: none !important;
        }
      `;
      document.head.appendChild(style);
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => {
      document.body.style.overflow = 'unset';
      document.body.style.pointerEvents = 'auto';
      // 移除样式覆盖
      const style = document.getElementById('confirm-dialog-override');
      if (style) {
        style.remove();
      }
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, handleKeyDown]);

  // Handle background click
  const handleBackgroundClick = (event: React.MouseEvent<HTMLDivElement>) => {
    // 阻止事件冒泡，防止点击穿透到下层元素
    event.stopPropagation();
    event.preventDefault();

    // 只有点击遮罩层本身时才关闭对话框
    if (event.target === event.currentTarget) {
      onCancel();
    }
  };

  // 阻止内容区域的点击事件传播
  const handleContentClick = (event: React.MouseEvent<HTMLDivElement>) => {
    event.stopPropagation();
  };

  if (!isOpen) {
    return null;
  }

  const variantStyles = {
    danger: 'bg-red-600 hover:bg-red-700 focus:ring-red-500',
    warning: 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500',
  };

  return createPortal(
    (
      <>
        {/* 背景遮罩 - 禁用所有背景交互 */}
        <div
          className="fixed inset-0 z-[9998] bg-transparent"
          style={{ pointerEvents: 'auto' }}
          aria-hidden="true"
        />
        {/* 对话框 */}
        <div
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-black bg-opacity-50"
          onClick={handleBackgroundClick}
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="confirm-dialog-title"
          aria-describedby="confirm-dialog-message"
          style={{ pointerEvents: 'auto' }}
        >
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4" onClick={handleContentClick}>
          {/* Header */}
          <div className="px-6 py-4 border-b border-gray-200">
            <h2
              id="confirm-dialog-title"
              className="text-lg font-semibold text-gray-900"
            >
              {title}
            </h2>
          </div>

          {/* Body */}
          <div className="px-6 py-4">
            <p
              id="confirm-dialog-message"
              className="text-sm text-gray-600 mb-4"
            >
              {message}
            </p>

            {/* Details section */}
            {details && (
              <div className="bg-gray-50 rounded-md p-3 space-y-2">
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 font-medium">K线数量:</span>
                  <span className="ml-2 text-gray-900">{details.count.toLocaleString()}</span>
                </div>
                <div className="flex items-center text-sm">
                  <span className="text-gray-600 font-medium">时间范围:</span>
                  <span className="ml-2 text-gray-900">
                    {details.startTime.split('T')[0]} ~ {details.endTime.split('T')[0]}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-400 transition-colors"
            >
              {cancelText}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className={`px-4 py-2 text-sm font-medium text-white rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors ${variantStyles[variant]}`}
            >
              {confirmText}
            </button>
          </div>
        </div>
      </div>
      </>
    ),
    document.body
  );
}
