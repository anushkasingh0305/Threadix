import { useSearchParams } from 'react-router-dom'
import { useInfiniteQuery } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { PageLayout } from '@/components/layout/PageLayout'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PAGE_SIZE } from '@/lib/constants'

export function FeedPage() {
  const [params] = useSearchParams()
  const mode = params.get('mode') === 'all' ? 'all' : 'feed'

  const fetchFn = (pageParam) => mode === 'feed'
    ? threadsApi.getFeed({ limit: PAGE_SIZE, offset: pageParam }).then(r => r.data)
    : threadsApi.getAll({  limit: PAGE_SIZE, offset: pageParam }).then(r => r.data)

  const { data, fetchNextPage, hasNextPage, isFetchingNextPage, refetch } =
    useInfiniteQuery({
      queryKey: ['threads', mode],
      queryFn:  ({ pageParam }) => fetchFn(pageParam),
      getNextPageParam: (last, pages) => {
        const loaded = pages.flatMap(p => p.threads).length
        return loaded < last.total ? loaded : undefined
      },
      initialPageParam: 0,
    })

  useWebSocket({
    channels: ['threads'],
    onMessage: (d) => { if (d.event === 'new_thread') refetch() },
  })

  const threads = data?.pages.flatMap(p => p.threads) ?? []

  return (
    <PageLayout>
      <div className='flex items-center justify-between mb-4'>
        <h1 className='text-lg font-semibold'>
          {mode === 'feed' ? 'Your feed' : 'All threads'}
        </h1>
      </div>

      <div className='space-y-3'>
        {threads.map(t => (
          <ThreadCard key={t.id} thread={t} />
        ))}
      </div>

      {hasNextPage && (
        <div className='flex justify-center mt-6'>
          <button onClick={() => fetchNextPage()} disabled={isFetchingNextPage}
            className='px-6 py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50'>
            {isFetchingNextPage ? 'Loading...' : 'Load more'}
          </button>
        </div>
      )}
    </PageLayout>
  )
}
