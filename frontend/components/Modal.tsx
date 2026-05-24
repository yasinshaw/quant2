'use client';

import { useEffect, useRef, ReactNode } from 'react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  variant?: 'success' | 'info' | 'error';
}

export default function Modal({
  isOpen,
  onClose,
  title,
  children,
  variant = 'info',
}: ModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // Close on ESC key press
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Close on background click
  const handleBackdropClick = (event: React.MouseEvent<HTMLDivElement>) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  if (!isOpen) return null;

  // Variant-specific styling
  const variantStyles = {
    success: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: '✓',
      iconBg: 'bg-green-500',
      title: 'text-green-900',
    },
    info: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'ℹ',
      iconBg: 'bg-blue-500',
      title: 'text-blue-900',
    },
    error: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: '✕',
      iconBg: 'bg-red-500',
      title: 'text-red-900',
    },
  };

  const styles = variantStyles[variant];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        ref={modalRef}
        className={`w-full max-w-md rounded-lg ${styles.bg} ${styles.border} border-2 shadow-xl`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-gray-200 p-4">
          <div className="flex items-center gap-3">
            <div
              className={`flex h-8 w-8 items-center justify-center rounded-full ${styles.iconBg} text-white`}
            >
              {styles.icon}
            </div>
            <h2
              id="modal-title"
              className={`text-lg font-semibold ${styles.title}`}
            >
              {title}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-2 text-gray-400 hover:bg-gray-200 hover:text-gray-600 transition-colors"
            aria-label="关闭"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path d="M6 18L18 6M6 6l12 12"></path>
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-6">{children}</div>

        {/* Footer */}
        <div className="flex justify-end border-t border-gray-200 p-4">
          <button
            onClick={onClose}
            className="rounded-lg bg-gray-600 px-4 py-2 text-white hover:bg-gray-700 transition-colors font-medium"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
