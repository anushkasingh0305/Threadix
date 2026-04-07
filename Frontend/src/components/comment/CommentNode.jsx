import { useState } from 'react'
import { Heart, ChevronDown, Pencil } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { commentsApi } from '@/api/comments'
import { useAuthStore } from '@/store/authStore'
import { useRole } from '@/hooks/useRole'
import { CommentInput } from './CommentInput'
import { MAX_COMMENT_DEPTH } from '@/lib/constants'
import { cn } from '@/lib/utils'

export function CommentNode({ comment, threadId }) {
  const [showReply,    setShowReply]    = useState(false)
  const [showChildren, setShowChildren] = useState(false)
  const [childOffset,  setChildOffset]  = useState(0)
  const [editing,      setEditing]      = useState(false)
  const [editContent,  setEditContent]  = useState(comment.content)
  const { user }        = useAuthStore()
  const { isModerator } = useRole()
  const qc = useQueryClient()

  const { data: children, isFetching } = useQuery({
    queryKey: ['comments', threadId, comment.id, 'children', childOffset],
    queryFn:  () => commentsApi.getChildren(threadId, comment.id, { limit: 5, offset: childOffset })
                      .then(r => r.data),
    enabled: showChildren,
  })

  const deleteMut = useMutation({
    mutationFn: () => commentsApi.delete(threadId, comment.id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['comments', threadId] }),
  })

  const editMut = useMutation({
    mutationFn: () => commentsApi.update(threadId, comment.id, { content: editContent }),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['comments', threadId] }); setEditing(false) },
  })

  const likeMut = useMutation({
    mutationFn: () => commentsApi.toggleLike(threadId, comment.id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['comments', threadId] }),
  })

  const replyMut = useMutation({
    mutationFn: (content) =>
      commentsApi.create(threadId, { content, parent_id: comment.id }).then(r => r.data),
    onSuccess: () => {
      setShowReply(false)
      setShowChildren(true)
      qc.invalidateQueries({ queryKey: ['comments', threadId, comment.id] })
    },
  })

  const canEdit   = user && user.id === comment.author?.id
  const canDelete = user && (user.id === comment.author?.id || isModerator)

  return (
    <div className='group'>
      <div className={comment.is_deleted
        ? 'p-3 rounded-lg bg-gray-50 border border-dashed border-gray-200'
        : 'p-3 rounded-lg border border-gray-200 bg-white'}>

        {comment.is_deleted ? (
          <p className='deleted-comment'>[This comment has been deleted]</p>
        ) : (
          <>
            <div className='flex items-center gap-2 mb-1.5'>
              <div className='w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center text-xs font-medium text-blue-700 overflow-hidden'>
                {comment.author?.avatar_url
                  ? <img src={comment.author.avatar_url} alt={comment.author.username}
                      className='w-5 h-5 rounded-full object-cover' />
                  : comment.author?.username.slice(0, 2).toUpperCase()}
              </div>
              <span className='text-xs font-medium'>{comment.author?.username}</span>
              <span className='text-xs text-gray-400'>
                {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
              </span>
            </div>

            {editing ? (
              <div className='mb-2 space-y-2'>
                <textarea value={editContent} onChange={e => setEditContent(e.target.value)} rows={3}
                  className='w-full px-2 py-1.5 text-sm border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-light' />
                <div className='flex gap-2'>
                  <button onClick={() => editMut.mutate()} disabled={editMut.isPending}
                    className='px-3 py-1 text-xs bg-brand text-white rounded-lg disabled:opacity-50'>
                    {editMut.isPending ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={() => setEditing(false)}
                    className='px-3 py-1 text-xs border rounded-lg hover:bg-gray-50'>Cancel</button>
                </div>
              </div>
            ) : (
              <p className='text-sm text-gray-800 mb-2 leading-relaxed'
                 dangerouslySetInnerHTML={{ __html:
                   comment.content.replace(/@(\w+)/g,
                     '<span class="text-blue-600 font-medium">@$1</span>')
                 }}
              />
            )}

            <div className='flex items-center gap-4 text-xs text-gray-400'>
              <button
                onClick={() => { if (user) likeMut.mutate() }}
                disabled={!user || likeMut.isPending}
                className={cn('flex items-center gap-1 hover:text-red-500 transition',
                  comment.user_has_liked && 'text-red-500')}>
                <Heart className='w-3 h-3' fill={comment.user_has_liked ? 'currentColor' : 'none'} />
                {comment.like_count}
              </button>
              {comment.depth < MAX_COMMENT_DEPTH && (
                <button onClick={() => setShowReply(v => !v)}
                  className='hover:text-brand transition'>Reply
                </button>
              )}
              {canEdit && !editing && (
                <button onClick={() => { setEditContent(comment.content); setEditing(true) }}
                  className='flex items-center gap-0.5 hover:text-brand transition'>
                  <Pencil className='w-3 h-3' /> Edit
                </button>
              )}
              {canDelete && (
                <button onClick={() => deleteMut.mutate()}
                  className='hover:text-red-500 transition'>Delete
                </button>
              )}
            </div>
          </>
        )}
      </div>

      {showReply && (
        <div className='mt-2 ml-4'>
          <CommentInput
            autoFocus
            placeholder={`Reply to @${comment.author?.username}...`}
            onSubmit={replyMut.mutateAsync}
          />
        </div>
      )}

      {comment.child_count > 0 && (
        <div className='mt-2 ml-5 border-l-2 border-gray-100 pl-3'>
          {!showChildren ? (
            <button onClick={() => setShowChildren(true)}
              className='flex items-center gap-1 text-xs text-brand hover:underline'>
              <ChevronDown className='w-3 h-3' />
              Load {comment.child_count} {comment.child_count === 1 ? 'reply' : 'replies'}
            </button>
          ) : (
            <>
              {(children?.comments ?? []).map((c) => (
                <div key={c.id} className='mb-2'>
                  <CommentNode comment={c} threadId={threadId} />
                </div>
              ))}
              {children && childOffset + 5 < children.total && (
                <button onClick={() => setChildOffset(o => o + 5)}
                  className='text-xs text-brand hover:underline mt-1'>
                  {isFetching ? 'Loading...' : 'Load more replies'}
                </button>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
