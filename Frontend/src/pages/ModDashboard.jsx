import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { PageLayout } from '@/components/layout/PageLayout'
import { PAGE_SIZE } from '@/lib/constants'

export function ModDashboard() {
  const qc = useQueryClient()
  const { data } = useQuery({
    queryKey: ['mod', 'threads'],
    queryFn: () => threadsApi.getAll({ limit: PAGE_SIZE, offset: 0 }).then(r => r.data),
  })

  const del = useMutation({
    mutationFn: (id) => threadsApi.delete(id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['mod', 'threads'] }),
  })

  const threads = data?.threads ?? []

  return (
    <PageLayout>
      <h1 className='text-xl font-semibold mb-5'>Moderator dashboard</h1>
      <div className='space-y-3'>
        {threads.map((t) => (
          <div key={t.id} className='relative'>
            <ThreadCard thread={t} />
            <button onClick={() => del.mutate(t.id)}
              className='absolute top-3 right-3 text-xs text-red-500 border border-red-200
                         rounded px-2 py-1 hover:bg-red-50 bg-white'>
              Delete thread
            </button>
          </div>
        ))}
      </div>
    </PageLayout>
  )
}
