import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi }  from '@/api/threads'
import { commentsApi } from '@/api/comments'
import { ThreadCard }  from '@/components/thread/ThreadCard'
import { CommentNode } from '@/components/comment/CommentNode'
import { CommentInput } from '@/components/comment/CommentInput'
import { PageLayout }  from '@/components/layout/PageLayout'
import { useWebSocket } from '@/hooks/useWebSocket'
import { PAGE_SIZE } from '@/lib/constants'

export function ThreadDetailPage() {
  const { id } = useParams()
  const threadId = Number(id)
  const qc = useQueryClient()
  const [commentOffset, setCommentOffset] = useState(0)

  const { data: thread } = useQuery({
    queryKey: ['thread', threadId],
    queryFn:  () => threadsApi.getOne(threadId).then(r => r.data),
  })

  const { data: commentData, refetch: refetchComments } = useQuery({
    queryKey: ['comments', threadId, commentOffset],
    queryFn:  () => commentsApi.getTopLevel(threadId, { limit: PAGE_SIZE, offset: commentOffset })
                      .then(r => r.data),
    enabled: !!threadId,
  })

  const createComment = useMutation({
    mutationFn: (content) => commentsApi.create(threadId, { content }).then(r => r.data),
    onSuccess:  () => refetchComments(),
  })

  useWebSocket({
    channels: [`thread:${threadId}:comments`, `thread:${threadId}:likes`],
    onMessage: (d) => {
      if (d.event === 'new_comment') refetchComments()
      if (d.event === 'like_update') qc.invalidateQueries({ queryKey: ['thread', threadId] })
    },
  })

  if (!thread) return <PageLayout><p className='text-sm text-gray-400'>Loading...</p></PageLayout>

  return (
    <PageLayout>
      <div className='max-w-2xl'>
        <ThreadCard thread={thread} />

        <div className='mt-6'>
          <h2 className='text-sm font-semibold text-gray-700 mb-3'>
            {commentData?.total ?? 0} comments
          </h2>
          <CommentInput onSubmit={createComment.mutateAsync} />
        </div>

        <div className='mt-6 space-y-3'>
          {(commentData?.comments ?? []).map(c => (
            <CommentNode key={c.id} comment={c} threadId={threadId} />
          ))}
        </div>

        {commentData && commentOffset + PAGE_SIZE < commentData.total && (
          <button onClick={() => setCommentOffset(o => o + PAGE_SIZE)}
            className='mt-4 w-full py-2 text-sm border border-gray-200 rounded-lg hover:bg-gray-50'>
            Load more comments
          </button>
        )}
      </div>
    </PageLayout>
  )
}
