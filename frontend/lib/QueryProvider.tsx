'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useRef } from 'react';
import { QueryClientSetup } from './QueryClientSetup';

export default function QueryProvider({ children }: { children: ReactNode }) {
  const queryClientRef = useRef<QueryClient>();

  if (!queryClientRef.current) {
    queryClientRef.current = new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 10 * 1000,
          gcTime: 5 * 60 * 1000,
          refetchOnWindowFocus: true,
          retry: 1,
          retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
        },
        mutations: {
          retry: false,
        },
      },
    });
  }

  return (
    <QueryClientProvider client={queryClientRef.current}>
      <QueryClientSetup />
      {children}
    </QueryClientProvider>
  );
}
