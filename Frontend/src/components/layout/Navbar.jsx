import { Link, useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api/auth'
import { NotifBell } from '@/components/notification/NotifBell'

export function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [q, setQ] = useState('')

  const handleSearch = (e) => {
    e.preventDefault()
    if (q.trim()) navigate(`/search?q=${encodeURIComponent(q)}`)
  }

  const handleLogout = async () => {
    await authApi.logout()
    logout()
    navigate('/login')
  }

  return (
    <nav className='sticky top-0 z-50 bg-white border-b border-gray-200 px-4 py-2.5'>
      <div className='max-w-7xl mx-auto flex items-center gap-4'>
        <Link to='/feed' className='text-lg font-semibold text-brand'>Threadix</Link>

        <form onSubmit={handleSearch} className='flex-1 max-w-md'>
          <div className='relative'>
            <Search className='absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400' />
            <input
              value={q} onChange={(e) => setQ(e.target.value)}
              placeholder='Search threads, tags...'
              className='w-full pl-9 pr-4 py-1.5 text-sm bg-gray-100 rounded-lg border-0
                         focus:outline-none focus:ring-2 focus:ring-brand-light'
            />
          </div>
        </form>

        <div className='ml-auto flex items-center gap-3'>
          {user ? (
            <>
              <NotifBell />
              <Link to='/threads/new'
                className='px-3 py-1.5 text-sm bg-brand text-white rounded-lg hover:bg-brand-light transition'>
                + New thread
              </Link>
              <div className='relative group'>
                <button className='flex items-center gap-2'>
                  <div className='w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center
                                  text-xs font-medium text-blue-700'>
                    {user.username.slice(0, 2).toUpperCase()}
                  </div>
                </button>
                <div className='absolute right-0 top-full mt-1 w-44 bg-white rounded-lg border
                                border-gray-200 shadow-sm hidden group-hover:block z-50'>
                  <Link to={`/profile/${user.username}`}
                    className='block px-4 py-2 text-sm hover:bg-gray-50'>Profile</Link>
                  {(user.role === 'moderator' || user.role === 'admin') && (
                    <Link to='/mod' className='block px-4 py-2 text-sm hover:bg-gray-50'>Mod dashboard</Link>
                  )}
                  {user.role === 'admin' && (
                    <Link to='/admin' className='block px-4 py-2 text-sm hover:bg-gray-50'>Admin dashboard</Link>
                  )}
                  <button onClick={handleLogout}
                    className='w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50'>
                    Log out
                  </button>
                </div>
              </div>
            </>
          ) : (
            <>
              <Link to='/login'    className='text-sm text-gray-600 hover:text-brand'>Log in</Link>
              <Link to='/register' className='px-3 py-1.5 text-sm bg-brand text-white rounded-lg'>Register</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
