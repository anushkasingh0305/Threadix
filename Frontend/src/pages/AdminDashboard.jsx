import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { PageLayout } from '@/components/layout/PageLayout'

export function AdminDashboard() {
  const { data: users, refetch } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => apiClient.get('/api/auth/user/list').then(r => r.data),
  })

  const updateRole = async (userId, role) => {
    await apiClient.patch(`/api/auth/user/${userId}/role`, { role })
    refetch()
  }

  const deleteUser = async (userId) => {
    if (!confirm('Delete this user?')) return
    await apiClient.delete(`/api/auth/user/${userId}`)
    refetch()
  }

  const usersData = users

  return (
    <PageLayout>
      <div className='max-w-4xl'>
        <h1 className='text-xl font-semibold mb-6'>Admin dashboard</h1>

        {/* Stat cards */}
        <div className='grid grid-cols-2 md:grid-cols-4 gap-3 mb-8'>
          {[['Users', usersData?.total ?? '-'], ['Threads', '-'], ['Comments', '-'], ['Mods', '-']]
            .map(([label, val]) => (
              <div key={label} className='bg-gray-50 rounded-xl p-4'>
                <p className='text-2xl font-semibold'>{val}</p>
                <p className='text-xs text-gray-400 mt-1'>{label}</p>
              </div>
            ))}
        </div>

        {/* Users table */}
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
              {(usersData?.users ?? []).map((u) => (
                <tr key={u.id} className='border-b last:border-0 hover:bg-gray-50'>
                  <td className='px-4 py-3 font-medium'>{u.username}</td>
                  <td className='px-4 py-3 text-gray-500'>{u.email}</td>
                  <td className='px-4 py-3'>
                    <select defaultValue={u.role}
                      onChange={e => updateRole(u.id, e.target.value)}
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
                      className='text-xs text-red-500 hover:underline'>Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  )
}
