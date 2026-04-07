import { Bell } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useNotifStore } from '@/store/notifStore'
import { useAuthStore } from '@/store/authStore'
import { notifsApi } from '@/api/notifications'
import { useWebSocket } from '@/hooks/useWebSocket'
import { useQuery } from '@tanstack/react-query'

export function NotifBell() {
  const { unreadCount, setCount, increment } = useNotifStore()
  const { user } = useAuthStore()

  useQuery({
    queryKey: ['notifs', 'unread'],
    queryFn: () => notifsApi.unreadCount().then(r => { setCount(r.data.unread_count); return r.data }),
    enabled: !!user,
  })

  useWebSocket({
    channels: user ? [`user:${user.id}:ws`] : [],
    enabled: !!user,
    onMessage: (data) => {
      if (data.type !== 'ping') increment()
    },
  })

  return (
    <Link to='/notifications' className='relative p-1.5 rounded-lg hover:bg-gray-100'>
      <Bell className='w-5 h-5 text-gray-600' />
      {unreadCount > 0 && (
        <span className='absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 text-white
                         text-xs rounded-full flex items-center justify-center font-medium'>
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </Link>
  )
}
