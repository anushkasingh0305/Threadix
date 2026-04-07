import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { commentsApi } from '@/api/comments'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { PageLayout } from '@/components/layout/PageLayout'
import { PAGE_SIZE } from '@/lib/constants'
import { formatDistanceToNow } from 'date-fns'

export function ModDashboard() {
  const [tab, setTab] = useState('threads')
  const [selectedThread, setSelectedThread] = useState(null)
  const qc = useQueryClient()

  const { data: threadData } = useQuery({
    queryKey: ['mod', 'threads'],
    queryFn: () => threadsApi.getAll({ limit: 50, offset: 0 }).then(r => r.data),
  })

  const { data: commentData } = useQuery({
    queryKey: ['mod', 'comments', selectedThread],
    queryFn: () => commentsApi.getTopLevel(selectedThread, { limit: 50, offset: 0 }).then(r => r.data),
    enabled: tab === 'comments' && !!selectedThread,
  })

  const delThread = useMutation({
    mutationFn: (id) => threadsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mod', 'threads'] }),
  })

  const delComment = useMutation({
    mutationFn: (commentId) => commentsApi.delete(selectedThread, commentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['mod', 'comments', selectedThread] }),
  })

  const threads = threadData?.threads ?? []

  return (
    <PageLayout>
      <h1 className='text-xl font-semibold mb-5'>Moderator dashboard</h1>

      {/* Tab switcher */}
      <div className='flex gap-1 mb-5 border-b'>
        {['threads', 'comments'].map(t => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize transition
              ${tab === t ? 'text-brand border-b-2 border-brand' : 'text-gray-400 hover:text-gray-600'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Threads tab */}
      {tab === 'threads' && (
        <div className='space-y-3'>
          {threads.map((t) => (
            <div key={t.id} className='relative'>
              <ThreadCard thread={t} />
              <button onClick={() => { if (confirm('Delete this thread?')) delThread.mutate(t.id) }}
                className='absolute top-3 right-3 text-xs text-red-500 border border-red-200
                           rounded px-2 py-1 hover:bg-red-50 bg-white'>
                Delete thread
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Comments tab */}
      {tab === 'comments' && (
        <div>
          <div className='mb-4'>
            <label className='text-sm font-medium text-gray-700'>Select a thread to manage comments</label>
            <select
              value={selectedThread ?? ''}
              onChange={e => setSelectedThread(Number(e.target.value) || null)}
              className='mt-1 w-full px-3 py-2 text-sm border rounded-lg bg-white'>
              <option value=''>-- Pick a thread --</option>
              {threads.map(t => (
                <option key={t.id} value={t.id}>{t.title}</option>
              ))}
            </select>
          </div>

          {selectedThread && (
            <div className='space-y-2'>
              {(commentData?.comments ?? []).length === 0 && (
                <p className='text-sm text-gray-400'>No comments on this thread.</p>
              )}
              {(commentData?.comments ?? []).map(c => (
                <div key={c.id} className='p-3 rounded-lg border border-gray-200 bg-white flex items-start gap-3'>
                  <div className='flex-1 min-w-0'>
                    <div className='flex items-center gap-2 mb-1'>
                      <span className='text-xs font-medium'>{c.author?.username}</span>
                      <span className='text-xs text-gray-400'>
                        {formatDistanceToNow(new Date(c.created_at), { addSuffix: true })}
                      </span>
                    </div>
                    <p className='text-sm text-gray-800'>{c.content}</p>
                  </div>
                  <button onClick={() => { if (confirm('Delete this comment?')) delComment.mutate(c.id) }}
                    className='text-xs text-red-500 border border-red-200 rounded px-2 py-1 hover:bg-red-50 flex-shrink-0'>
                    Delete
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </PageLayout>
  )
}
