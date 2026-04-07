import { Link, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { tagsApi } from '@/api/tags'
import { cn } from '@/lib/utils'

const NAV = [
  { label: 'My feed',       to: '/feed' },
  { label: 'All threads',   to: '/feed?mode=all' },
  { label: 'Notifications', to: '/notifications' },
]

export function Sidebar() {
  const loc = useLocation()
  const { data: tags } = useQuery({
    queryKey: ['tags'],
    queryFn: () => tagsApi.getAll().then(r => r.data),
    staleTime: 5 * 60_000,
  })

  return (
    <aside className='w-52 flex-shrink-0 sticky top-20 self-start hidden md:block'>
      <nav className='space-y-0.5 mb-6'>
        {NAV.map(n => (
          <Link key={n.to} to={n.to}
            className={cn('block px-3 py-2 text-sm rounded-lg transition',
              loc.pathname + loc.search === n.to
                ? 'bg-blue-50 text-brand font-medium'
                : 'text-gray-600 hover:bg-gray-100'
            )}>
            {n.label}
          </Link>
        ))}
      </nav>

      <div>
        <p className='text-xs font-medium text-gray-400 uppercase tracking-wide px-3 mb-2'>Tags</p>
        <div className='flex flex-wrap gap-1.5 px-1'>
          {(tags?.slice(0, 12) ?? []).map((tag) => (
            <Link key={tag.id} to={`/search?q=${tag.name}`} className='tag-pill hover:bg-blue-100'>
              {tag.name}
            </Link>
          ))}
        </div>
      </div>
    </aside>
  )
}
