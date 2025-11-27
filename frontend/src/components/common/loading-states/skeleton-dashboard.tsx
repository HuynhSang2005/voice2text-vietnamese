/**
 * Skeleton Dashboard/Transcription Page
 * 
 * Loading state skeleton for the main transcription page
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

export function SkeletonTranscription() {
  return (
    <div className="flex flex-col gap-6 p-6 max-w-[1400px] mx-auto">
      {/* Header skeleton */}
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        <Skeleton className="h-9 w-32" />
      </div>

      {/* Main content grid */}
      <div className="grid gap-6 lg:grid-cols-[350px_1fr]">
        {/* Left panel - Audio controls */}
        <div className="space-y-6">
          {/* Audio Input Card */}
          <Card>
            <CardHeader className="pb-4">
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-4 w-40 mt-1" />
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Model selector skeleton */}
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-10 w-full" />
              </div>

              {/* Device selector skeleton */}
              <div className="space-y-2">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-10 w-full" />
              </div>

              {/* Record button skeleton */}
              <div className="flex flex-col items-center gap-4 py-4">
                <Skeleton className="h-20 w-20 rounded-full" />
                <Skeleton className="h-4 w-32" />
              </div>

              {/* Volume meter skeleton */}
              <div className="space-y-2">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-8" />
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            </CardContent>
          </Card>

          {/* Stats card skeleton */}
          <Card>
            <CardHeader className="pb-4">
              <Skeleton className="h-5 w-20" />
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="space-y-1">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-6 w-12" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right panel - Transcription view */}
        <Card className="flex flex-col min-h-[500px]">
          <CardHeader className="border-b pb-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </div>
              <Skeleton className="h-9 w-24" />
            </div>
          </CardHeader>
          <CardContent className="flex-1 p-4">
            {/* Transcript lines skeleton */}
            <div className="space-y-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="flex gap-3">
                  <Skeleton className="h-4 w-16 flex-shrink-0" />
                  <Skeleton 
                    className="h-4 flex-1" 
                    style={{ width: `${60 + Math.random() * 35}%` }} 
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

/**
 * Compact skeleton for inline loading
 */
export function SkeletonTranscriptionCompact() {
  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center gap-4">
        <Skeleton className="h-12 w-12 rounded-full" />
        <div className="space-y-2 flex-1">
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      </div>
      <Skeleton className="h-32 w-full rounded-lg" />
    </div>
  )
}

export default SkeletonTranscription
