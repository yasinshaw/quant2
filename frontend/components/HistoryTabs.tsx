'use client';

interface HistoryTabsProps {
  activeTab: 'backtest' | 'optimization';
  onTabChange: (tab: 'backtest' | 'optimization') => void;
}

export default function HistoryTabs({ activeTab, onTabChange }: HistoryTabsProps) {
  const tabs = [
    { id: 'backtest' as const, label: 'Backtests' },
    { id: 'optimization' as const, label: 'Optimizations' },
  ];

  return (
    <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
      {tabs.map(({ id, label }) => {
        const isActive = activeTab === id;
        return (
          <button
            key={id}
            onClick={() => onTabChange(id)}
            className={`px-4 py-2 rounded-md font-medium transition-all duration-200 cursor-pointer ${
              isActive
                ? 'bg-white dark:bg-slate-700 text-primary-700 dark:text-primary-400 shadow-sm'
                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100'
            }`}
            aria-current={isActive ? 'page' : undefined}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
