'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { toast } from './toast';

export function QueryClientSetup() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // 全局错误处理：捕获所有查询错误
    const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
      if (event?.type === 'updated' && event.action.type === 'error') {
        const error = event.action.error as any;
        const errorMessage = error?.response?.data?.detail || error?.message || '请求失败';
        console.error('Query error:', error);
        toast.error(errorMessage);
      }
    });

    // 全局错误处理：捕获所有突变错误
    const unsubscribeMutation = queryClient.getMutationCache().subscribe((event) => {
      if (event?.type === 'updated' && event.action.type === 'error') {
        const error = event.action.error as any;
        const errorMessage = error?.response?.data?.detail || error?.message || '操作失败';
        console.error('Mutation error:', error);
        toast.error(errorMessage);
      }
    });

    return () => {
      unsubscribe();
      unsubscribeMutation();
    };
  }, [queryClient]);

  return null;
}
