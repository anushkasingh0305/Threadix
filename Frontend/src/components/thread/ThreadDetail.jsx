import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, MessageCircle, Eye, Pencil, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { threadsApi } from '@/api/threads'
import { useAuthStore } from '@/store/authStore'
import { useRole } from '@/hooks/useRole'
import { cn } from '@/lib/utils'

export function ThreadDetail({ thread }) {
  const { user }        = useAuthStore()
  const { isModerator } = useRole()
  const qc = useQueryClient()

  const [editing,   setEditing]   = useState(false)
  const [editTitle, setEditTitle] = useState(thread.title)
  const [editDesc,  setEditDesc]  = useState(thread.description)

  const canEdit   = user && user.id === thread.author.id
  const canDelete = user && (user.id === thread.author.id || isModerator)

  const likeMut = useMutation({
    mutationFn: () => threadsApi.toggleLike(thread.id),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['thread', thread.id] }),
  })

  const editMut = useMutation({
    mutationFn: () => threadsApi.update(thread.id, { title: editTitle, description: editDesc }),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['thread', thread.id] }); setEditing(false) },
  })

  const deleteMut = useMutation({
    mutationFn: () => threadsApi.delete(thread.id),
    onSuccess:  () => { window.location.href = '/feed' },
  })

  return (
    <div className='card'>
      {/* Author row */}
      <div className='flex items-center gap-2 mb-3'>
        <div className='w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center
                        text-xs font-medium text-blue-700'>
          {thread.author.username.slice(0, 2).toUpperCase()}
        </div>
        <div>
          <Link to={`/profile/${thread.author.username}`}
            className='text-sm font-medium text-gray-900 hover:text-brand'>
            {thread.author.username}
          </Link>
          <p className='text-xs text-gray-400'>
            {formatDistanceToNow(new Date(thread.created_at), { addSuffix: true })}
          </p>
        </div>
        <div className='ml-auto flex items-center gap-2'>
          {canEdit && !editing && (
            <button onClick={() => { setEditTitle(thread.title); setEditDesc(thread.description); setEditing(true) }}
              className='flex items-center gap-1 text-xs text-gray-500 border rounded-lg px-2 py-1 hover:bg-gray-50'>
              <Pencil className='w-3 h-3' /> Edit
            </button>
          )}
          {canDelete && (
            <button onClick={() => { if (confirm('Delete this thread?')) deleteMut.mutate() }}
              className='flex items-center gap-1 text-xs text-red-500 border border-red-200 rounded-lg px-2 py-1 hover:bg-red-50'>
              <Trash2 className='w-3 h-3' /> Delete
            </button>
          )}
        </div>
      </div>

      {editing ? (
        <div className='space-y-3 mb-4'>
          <input value={editTitle} onChange={e => setEditTitle(e.target.value)} maxLength={200}
            className='w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-light font-semibold' />
          <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={5}
            className='w-full px-3 py-2 text-sm border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-light' />
          <div className='flex gap-2'>
            <button onClick={() => editMut.mutate()} disabled={editMut.isPending}
              className='px-4 py-1.5 text-sm bg-brand text-white rounded-lg hover:bg-brand-light disabled:opacity-50'>
              {editMut.isPending ? 'Saving...' : 'Save'}
            </button>
            <button onClick={() => setEditing(false)}
              className='px-4 py-1.5 text-sm border rounded-lg hover:bg-gray-50'>Cancel</button>
          </div>
        </div>
      ) : (
        <>
          <h1 className='text-xl font-semibold text-gray-900 mb-3'>{thread.title}</h1>
          <p className='text-sm text-gray-700 leading-relaxed mb-4 whitespace-pre-wrap'
             dangerouslySetInnerHTML={{ __html:
               thread.description.replace(/@(\w+)/g,
                 '<span class="text-blue-600 font-medium">@$1</span>')
             }}
          />
        </>
      )}

      {/* Media */}
      {thread.media_urls.length > 0 && (
        <div className='grid grid-cols-2 gap-2 mb-4'>
          {thread.media_urls.map((url, i) => (
            <img key={i} src={url} alt=''
              className='w-full rounded-lg object-cover max-h-64' />
          ))}
        </div>
      )}

      {/* Tags */}
      {thread.tags.length > 0 && (
        <div className='flex flex-wrap gap-1.5 mb-4'>
          {thread.tags.map(t => (
            <Link key={t.id} to={`/search?q=${t.name}`} className='tag-pill hover:bg-blue-100'>
              {t.name}
            </Link>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className='flex items-center gap-4 text-sm text-gray-500 pt-3 border-t'>
        <button onClick={() => likeMut.mutate()} disabled={likeMut.isPending}
          className={cn('flex items-center gap-1.5 hover:text-red-500 transition',
            thread.user_has_liked && 'text-red-500')}>
          <Heart className='w-4 h-4' fill={thread.user_has_liked ? 'currentColor' : 'none'} />
          {thread.like_count} likes
        </button>
        <span className='flex items-center gap-1.5'>
          <MessageCircle className='w-4 h-4' />
          {thread.comment_count} comments
        </span>
        <span className='flex items-center gap-1.5'>
          <Eye className='w-4 h-4' />
          {thread.view_count} views
        </span>
      </div>
    </div>
  )
}
