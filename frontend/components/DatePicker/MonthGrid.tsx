'use client';

import React from 'react';

interface MonthGridProps {
  currentMonth: Date;
  onSelectMonth: (monthIndex: number) => void;
  onClose: () => void;
}

const MONTHS = [
  '1月', '2月', '3月', '4月', '5月', '6月',
  '7月', '8月', '9月', '10月', '11月', '12月'
];

export default function MonthGrid({ currentMonth, onSelectMonth, onClose }: MonthGridProps) {
  const currentMonthIndex = currentMonth.getMonth();

  const handleMonthClick = (monthIndex: number) => {
    onSelectMonth(monthIndex);
    onClose();
  };

  return (
    <div className="absolute top-full left-0 mt-2 bg-white dark:bg-slate-700 rounded-lg shadow-lg border border-slate-200 dark:border-slate-600 p-4 z-50">
      <div className="grid grid-cols-3 gap-2">
        {MONTHS.map((month, index) => (
          <button
            key={month}
            onClick={() => handleMonthClick(index)}
            className={`px-4 py-2 rounded-lg text-sm transition-colors ${
              index === currentMonthIndex
                ? 'bg-primary-600 dark:bg-primary-500 text-white'
                : 'hover:bg-slate-100 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200'
            }`}
          >
            {month}
          </button>
        ))}
      </div>
    </div>
  );
}
