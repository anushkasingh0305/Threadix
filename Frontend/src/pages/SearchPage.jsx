import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { searchApi } from '@/api/search'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { PageLayout } from '@/components/layout/PageLayout'
import { PAGE_SIZE } from '@/lib/constants'

export function SearchPage() {
  const [params] = useSearchParams()
  const q = params.get('q') ?? ''

  const { data, isLoading } = useQuery({
    queryKey: ['search', q],
    queryFn:  () => searchApi.threads(q, { limit: PAGE_SIZE, offset: 0 }).then(r => r.data),
    enabled:  q.length > 0,
  })

  const threads = data?.threads ?? []

  return (
    <PageLayout>
      <h1 className='text-lg font-semibold mb-4'>
        {q ? `Results for "${q}"` : 'Search'}
      </h1>
      {isLoading && <p className='text-sm text-gray-400'>Searching...</p>}
      <div className='space-y-3'>
        {threads.map((t) => <ThreadCard key={t.id} thread={t} />)}
        {!isLoading && q && threads.length === 0 && (
          <p className='text-sm text-gray-400'>No threads found for "{q}"</p>
        )}
      </div>
    </PageLayout>
  )
}
