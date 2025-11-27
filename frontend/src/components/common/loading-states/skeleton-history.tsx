/**
 * Skeleton History Page
 * 
 * Loading state skeleton for the history/transcription logs page
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function SkeletonHistory() {
  return (
    <div className="flex flex-col h-full gap-6 max-w-[1600px] mx-auto p-6">
      {/* Header skeleton */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Skeleton className="h-10 w-10 rounded-lg" />
          <div className="space-y-1">
            <Skeleton className="h-7 w-56" />
            <Skeleton className="h-4 w-72" />
          </div>
        </div>
        <Skeleton className="h-10 w-40 rounded-lg" />
      </div>

      {/* Main Content Card */}
      <Card className="flex-1 overflow-hidden flex flex-col">
        {/* Filters Header */}
        <CardHeader className="border-b py-4 px-6">
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4">
            {/* Search skeleton */}
            <Skeleton className="h-9 w-full md:max-w-md" />
            
            {/* Filter buttons skeleton */}
            <div className="flex items-center gap-2">
              <Skeleton className="h-9 w-24" />
              <Skeleton className="h-9 w-36" />
            </div>
          </div>
        </CardHeader>

        {/* Table Content */}
        <CardContent className="p-0 flex-1">
          {/* Table header skeleton */}
          <div className="bg-muted/30 border-b px-6 py-3">
            <div className="grid grid-cols-6 gap-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-full max-w-[200px]" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-16 ml-auto" />
            </div>
          </div>

          {/* Table rows skeleton */}
          <div className="divide-y">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-6 py-4">
                <div className="grid grid-cols-6 gap-4 items-center">
                  {/* Session ID */}
                  <div className="flex items-center gap-2">
                    <Skeleton className="h-7 w-7 rounded-md" />
                    <Skeleton className="h-4 w-16" />
                  </div>
                  
                  {/* Date & Time */}
                  <div className="space-y-1">
                    <Skeleton className="h-4 w-24" />
                    <Skeleton className="h-3 w-16" />
                  </div>
                  
                  {/* Model */}
                  <Skeleton className="h-5 w-20 rounded-full" />
                  
                  {/* Content */}
                  <Skeleton 
                    className="h-4" 
                    style={{ width: `${50 + Math.random() * 45}%` }} 
                  />
                  
                  {/* Latency */}
                  <Skeleton className="h-4 w-14" />
                  
                  {/* Actions */}
                  <div className="flex justify-end gap-1">
                    <Skeleton className="h-7 w-7 rounded" />
                    <Skeleton className="h-7 w-7 rounded" />
                    <Skeleton className="h-7 w-7 rounded" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>

        {/* Pagination footer skeleton */}
        <div className="border-t p-4 flex items-center justify-between">
          <Skeleton className="h-4 w-32" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-8" />
            <Skeleton className="h-4 w-6" />
            <Skeleton className="h-8 w-8" />
          </div>
        </div>
      </Card>
    </div>
  )
}

/**
 * Skeleton for history table rows only
 */
export function SkeletonHistoryRows({ count = 5 }: { count?: number }) {
  return (
    <div className="divide-y">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="px-6 py-4">
          <div className="grid grid-cols-6 gap-4 items-center">
            <div className="flex items-center gap-2">
              <Skeleton className="h-7 w-7 rounded-md" />
              <Skeleton className="h-4 w-16" />
            </div>
            <div className="space-y-1">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-3 w-16" />
            </div>
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-14" />
            <div className="flex justify-end gap-1">
              <Skeleton className="h-7 w-7 rounded" />
              <Skeleton className="h-7 w-7 rounded" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default SkeletonHistory
