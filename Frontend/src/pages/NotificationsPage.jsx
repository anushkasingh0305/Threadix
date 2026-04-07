import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { notifsApi } from '@/api/notifications'
import { useNotifStore } from '@/store/notifStore'
import { PageLayout } from '@/components/layout/PageLayout'
import { cn } from '@/lib/utils'

const TYPE_ICON  = { reply: '💬', mention: '@', like: '♥', comment: '💬' }
const TYPE_LABEL = {
  reply:   'replied to your comment',
  mention: 'mentioned you',
  like:    'liked your thread',
  comment: 'commented on your thread',
}

export function NotificationsPage() {
  const qc = useQueryClient()
  const { reset, setCount, unreadCount } = useNotifStore()

  const { data } = useQuery({
    queryKey: ['notifications'],
    queryFn:  () => notifsApi.getAll({ limit: 50, offset: 0 }).then(r => r.data),
  })

  const markRead = useMutation({
    mutationFn: (id) => notifsApi.markRead(id),
    onSuccess: () => {
      setCount(Math.max(0, unreadCount - 1))
      qc.invalidateQueries({ queryKey: ['notifications'] })
      qc.invalidateQueries({ queryKey: ['notifs', 'unread'] })
    },
  })

  const markAll = useMutation({
    mutationFn: notifsApi.markAllRead,
    onSuccess: () => { reset(); qc.invalidateQueries({ queryKey: ['notifications'] }); qc.invalidateQueries({ queryKey: ['notifs', 'unread'] }) },
  })

  const notifications = data?.notifications ?? []

  return (
    <PageLayout>
      <div className='max-w-xl'>
        <div className='flex items-center justify-between mb-5'>
          <h1 className='text-xl font-semibold'>Notifications</h1>
          <button onClick={() => markAll.mutate()}
            className='text-sm text-brand hover:underline'>Mark all read
          </button>
        </div>

        <div className='space-y-1'>
          {notifications.map((n) => (
            <Link key={n.id} to={n.thread_id ? `/threads/${n.thread_id}` : '#'}
              onClick={() => { if (!n.is_read) markRead.mutate(n.id) }}
              className={cn('flex items-start gap-3 p-3 rounded-lg transition',
                !n.is_read ? 'bg-blue-50 hover:bg-blue-100' : 'hover:bg-gray-50'
              )}>
              <div className={cn('w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0',
                n.type === 'reply'   ? 'bg-blue-100' :
                n.type === 'mention' ? 'bg-green-100' : 'bg-red-100'
              )}>
                {TYPE_ICON[n.type] ?? '🔔'}
              </div>
              <div className='flex-1 min-w-0'>
                <p className='text-sm text-gray-900'>
                  <span className='font-medium'>{n.actor_username ?? `user_${n.actor_id}`}</span>
                  {' '}{TYPE_LABEL[n.type] ?? 'sent a notification'}
                </p>
                <p className='text-xs text-gray-400 mt-0.5'>
                  {formatDistanceToNow(new Date(n.created_at), { addSuffix: true })}
                </p>
              </div>
              {!n.is_read && (
                <div className='w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0' />
              )}
            </Link>
          ))}
          {notifications.length === 0 && (
            <p className='text-sm text-gray-400 text-center py-8'>No notifications yet</p>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
