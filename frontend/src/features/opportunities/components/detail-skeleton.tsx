import { Skeleton } from '@/components/ui/skeleton'

export function DetailSkeleton() {
  return (
    <div className="grid grid-cols-[minmax(0,732px)_300px] gap-14">
      <div className="flex flex-col gap-10">
        <Skeleton className="h-20" />
        <Skeleton className="h-40" />
        <Skeleton className="h-52" />
      </div>
      <Skeleton className="h-64" />
    </div>
  )
}
