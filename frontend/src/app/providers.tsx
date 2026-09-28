import { useState, type ReactNode } from 'react'
import { MutationCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from '@/components/common/toaster'
import { ApiError, errorMessage } from '@/lib/api-client'
import { toast } from '@/lib/toast'

function createQueryClient(): QueryClient {
  return new QueryClient({
    mutationCache: new MutationCache({
      // Every write announces its own failure here, so no feature has to remember to.
      onError: (error) => {
        // Except a rejected payload: the form marks the offending inputs instead.
        if (error instanceof ApiError && error.fields.length > 0) return
        toast(errorMessage(error))
      },
    }),
  })
}

export function AppProviders({ children }: { children: ReactNode }) {
  const [queryClient] = useState(createQueryClient)

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
        <Toaster />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
