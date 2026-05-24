'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { optimizationApi, OptimizationResponse } from '@/lib/api/optimization';
import OptimizationForm from '@/components/OptimizationForm';
import OptimizationResults from '@/components/OptimizationResults';
import { toast } from '@/lib/toast';

export default function OptimizePage() {
  const [results, setResults] = useState<OptimizationResponse | null>(null);
  const [strategyName, setStrategyName] = useState<string>('');

  const optimizeMutation = useMutation({
    mutationFn: optimizationApi.run,
    onSuccess: (data) => {
      toast.success('Optimization completed successfully');
      setResults(data);
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to run optimization');
      setResults(null);
    },
  });

  const handleSubmit = (request: any) => {
    setStrategyName(request.strategy_name || '');
    optimizeMutation.mutate(request);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Parameter Optimization</h1>
          <p className="text-gray-600 mt-2">
            Perform grid search optimization to find the best parameters for your strategy
          </p>
        </div>

        <OptimizationForm
          onSubmit={handleSubmit}
          isLoading={optimizeMutation.isPending}
        />

        {results && <OptimizationResults result={results} strategyName={strategyName} />}
      </div>
    </div>
  );
}
