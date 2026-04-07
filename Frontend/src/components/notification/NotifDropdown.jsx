import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { notifsApi } from '@/api/notifications'
import { formatDistanceToNow } from 'date-fns'
import { cn } from '@/lib/utils'

const TYPE_ICON = { reply: '💬', mention: '@', like: '♥', comment: '💬' }

export function NotifDropdown() {
  const { data } = useQuery({
    queryKey: ['notifs', 'dropdown'],
    queryFn:  () => notifsApi.getAll({ limit: 5, offset: 0 }).then(r => r.data),
    staleTime: 30_000,
  })

  const notifications = data?.notifications ?? []

  return (
    <div className='w-80 bg-white rounded-lg border border-gray-200 shadow-lg overflow-hidden'>
      <div className='px-4 py-3 border-b flex items-center justify-between'>
        <span className='text-sm font-semibold'>Notifications</span>
        <Link to='/notifications' className='text-xs text-brand hover:underline'>See all</Link>
      </div>
      {notifications.length === 0 ? (
        <p className='px-4 py-5 text-sm text-gray-400 text-center'>No notifications yet</p>
      ) : (
        notifications.map(n => (
          <Link key={n.id} to={n.thread_id ? `/threads/${n.thread_id}` : '#'}
            className={cn('flex items-center gap-3 px-4 py-3 text-sm transition',
              !n.is_read ? 'bg-blue-50 hover:bg-blue-100' : 'hover:bg-gray-50')}>
            <span className='text-base'>{TYPE_ICON[n.type] ?? '🔔'}</span>
            <div className='flex-1 min-w-0'>
              <p className='text-xs text-gray-500'>
                {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
              </p>
            </div>
            {!n.is_read && <div className='w-2 h-2 bg-blue-500 rounded-full flex-shrink-0' />}
          </Link>
        ))
      )}
    </div>
  )
}
