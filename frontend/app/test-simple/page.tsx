'use client';

import { useEffect, useState } from 'react';

export default function TestSimplePage() {
  const [count, setCount] = useState(0);

  useEffect(() => {
    console.log('[TestSimplePage] Component mounted');
    const interval = setInterval(() => {
      setCount(c => c + 1);
      console.log('[TestSimplePage] Count:', count);
    }, 1000);

    return () => clearInterval(interval);
  }, [count]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-slate-900 p-8">
      <div className="max-w-7xl mx-auto">
        <h1 className="text-2xl font-bold mb-4">Simple Test Page</h1>
        <p className="text-lg">Count: {count}</p>
        <button
          onClick={() => setCount(c => c + 1)}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Increment
        </button>
      </div>
    </div>
  );
}
