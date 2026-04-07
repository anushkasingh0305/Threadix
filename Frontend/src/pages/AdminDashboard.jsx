import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { threadsApi } from '@/api/threads'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { PageLayout } from '@/components/layout/PageLayout'

export function AdminDashboard() {
  const [tab, setTab] = useState('users')
  const qc = useQueryClient()

  const { data: users, refetch: refetchUsers } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => apiClient.get('/api/auth/user/list').then(r => r.data),
  })

  const { data: stats } = useQuery({
    queryKey: ['admin', 'stats'],
    queryFn: () => apiClient.get('/api/threads/stats').then(r => r.data),
  })

  const { data: threadData } = useQuery({
    queryKey: ['admin', 'threads'],
    queryFn: () => threadsApi.getAll({ limit: 50, offset: 0 }).then(r => r.data),
    enabled: tab === 'threads',
  })

  const updateRole = async (username, role) => {
    await apiClient.put(`/api/auth/user/role/${username}`, null, { params: { role } })
    refetchUsers()
  }

  const deleteUser = async (userId) => {
    if (!confirm('Delete this user?')) return
    await apiClient.delete(`/api/auth/user/delete/${userId}`)
    refetchUsers()
  }

  const delThread = useMutation({
    mutationFn: (id) => threadsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'threads'] }),
  })

  const tabs = ['users', 'threads']

  return (
    <PageLayout>
      <div className='max-w-4xl'>
        <h1 className='text-xl font-semibold mb-6'>Admin dashboard</h1>

        {/* Stat cards */}
        <div className='grid grid-cols-2 md:grid-cols-4 gap-3 mb-8'>
          {[
            ['Users', users?.total ?? '-'],
            ['Threads', stats?.threads ?? '-'],
            ['Comments', stats?.comments ?? '-'],
            ['Mods', users?.mods ?? '-'],
          ].map(([label, val]) => (
            <div key={label} className='bg-gray-50 rounded-xl p-4'>
              <p className='text-2xl font-semibold'>{val}</p>
              <p className='text-xs text-gray-400 mt-1'>{label}</p>
            </div>
          ))}
        </div>

        {/* Tab switcher */}
        <div className='flex gap-1 mb-5 border-b'>
          {tabs.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2 text-sm font-medium capitalize transition
                ${tab === t ? 'text-brand border-b-2 border-brand' : 'text-gray-400 hover:text-gray-600'}`}>
              {t}
            </button>
          ))}
        </div>

        {/* Users tab */}
        {tab === 'users' && (
          <div className='card overflow-hidden p-0'>
            <table className='w-full text-sm'>
              <thead className='bg-gray-50 border-b'>
                <tr>
                  {['User', 'Email', 'Role', 'Joined', ''].map(h => (
                    <th key={h} className='text-left text-xs font-medium text-gray-500 px-4 py-3'>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(users?.users ?? []).map((u) => (
                  <tr key={u.id} className='border-b last:border-0 hover:bg-gray-50'>
                    <td className='px-4 py-3 font-medium'>{u.username}</td>
                    <td className='px-4 py-3 text-gray-500'>{u.email}</td>
                    <td className='px-4 py-3'>
                      <select defaultValue={u.role}
                        onChange={e => updateRole(u.username, e.target.value)}
                        className='text-xs border rounded px-2 py-1 bg-white'>
                        <option value='member'>member</option>
                        <option value='moderator'>moderator</option>
                        <option value='admin'>admin</option>
                      </select>
                    </td>
                    <td className='px-4 py-3 text-gray-400 text-xs'>
                      {new Date(u.created_at).toLocaleDateString()}
                    </td>
                    <td className='px-4 py-3'>
                      <button onClick={() => deleteUser(u.id)}
                        className='text-xs text-red-500 hover:underline'>Delete</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Threads tab */}
        {tab === 'threads' && (
          <div className='space-y-3'>
            {(threadData?.threads ?? []).map(t => (
              <div key={t.id} className='relative'>
                <ThreadCard thread={t} />
                <button onClick={() => { if (confirm('Delete this thread?')) delThread.mutate(t.id) }}
                  className='absolute top-3 right-3 text-xs text-red-500 border border-red-200
                             rounded px-2 py-1 hover:bg-red-50 bg-white'>
                  Delete thread
                </button>
              </div>
            ))}
            {(threadData?.threads ?? []).length === 0 && (
              <p className='text-sm text-gray-400'>No threads.</p>
            )}
          </div>
        )}
      </div>
    </PageLayout>
  )
}
