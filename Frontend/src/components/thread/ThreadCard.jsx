import { Link } from 'react-router-dom'
import { Heart, MessageCircle, Eye } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

export function ThreadCard({ thread }) {
  if (thread.is_deleted) return null

  const { user } = useAuthStore()
  const qc = useQueryClient()

  const likeMut = useMutation({
    mutationFn: () => threadsApi.toggleLike(thread.id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['threads'] }),
  })

  return (
    <div className='card hover:border-gray-300 transition group'>
      <div className='flex gap-3'>
        <div className='flex-1 min-w-0'>
          {/* Author row */}
          <div className='flex items-center gap-2 mb-2'>
            <div className='w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center
                            text-xs font-medium text-blue-700 flex-shrink-0'>
              {thread.author.username.slice(0, 2).toUpperCase()}
            </div>
            <Link to={`/profile/${thread.author.username}`}
              className='text-sm font-medium text-gray-900 hover:text-brand'>
              {thread.author.username}
            </Link>
            <span className='text-xs text-gray-400'>
              {formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}
            </span>
          </div>

          {/* Title */}
          <Link to={`/threads/${thread.id}`}>
            <h2 className='text-base font-semibold text-gray-900 mb-1.5
                           group-hover:text-brand transition line-clamp-2'>
              {thread.title}
            </h2>
          </Link>

          {/* Description preview */}
          <p className='text-sm text-gray-500 mb-3 line-clamp-2'>{thread.description}</p>

          {/* Tags */}
          {thread.tags.length > 0 && (
            <div className='flex flex-wrap gap-1.5 mb-3'>
              {thread.tags.map(t => (
                <span key={t.id} className='tag-pill'>{t.name}</span>
              ))}
            </div>
          )}

          {/* Action bar */}
          <div className='flex items-center gap-4 text-xs text-gray-400'>
            <button
              onClick={e => { e.preventDefault(); if (user) likeMut.mutate() }}
              disabled={!user || likeMut.isPending}
              className={cn('flex items-center gap-1 transition hover:text-red-500',
                thread.user_has_liked && 'text-red-500')}>
              <Heart className='w-3.5 h-3.5' fill={thread.user_has_liked ? 'currentColor' : 'none'} />
              {thread.like_count}
            </button>
            <span className='flex items-center gap-1'>
              <MessageCircle className='w-3.5 h-3.5' />
              {thread.comment_count}
            </span>
            <span className='flex items-center gap-1'>
              <Eye className='w-3.5 h-3.5' />
              {thread.view_count}
            </span>
          </div>
        </div>

        {/* Media thumbnail */}
        {thread.media_urls[0] && (
          <img src={thread.media_urls[0]} alt=''
            className='w-20 h-16 object-cover rounded-lg flex-shrink-0' />
        )}
      </div>
    </div>
  )
}
