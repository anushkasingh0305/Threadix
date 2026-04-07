import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { authApi } from '@/api/auth'
import { threadsApi } from '@/api/threads'
import { PageLayout } from '@/components/layout/PageLayout'
import { useAuthStore } from '@/store/authStore'
import { ThreadCard } from '@/components/thread/ThreadCard'
import { formatDistanceToNow } from 'date-fns'
import { Pencil, X, Lock } from 'lucide-react'

export function ProfilePage() {
  const { username } = useParams()
  const { user, setUser } = useAuthStore()
  const qc = useQueryClient()
  const navigate = useNavigate()

  const [editing,     setEditing]     = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newBio,      setNewBio]      = useState('')
  const [avatarFile,  setAvatarFile]  = useState(null)
  const [editError,   setEditError]   = useState('')
  const [changingPw,   setChangingPw]   = useState(false)
  const [currentPw,    setCurrentPw]    = useState('')
  const [newPw,        setNewPw]        = useState('')
  const [pwError,      setPwError]      = useState('')
  const [pwSuccess,    setPwSuccess]    = useState('')

  const { data: profile, isLoading } = useQuery({
    queryKey: ['profile', username],
    queryFn:  () => apiClient.get(`/api/auth/user/${username}`).then(r => r.data),
    enabled:  !!username,
  })

  const isOwnProfile = user?.username === username

  const { data: userThreads } = useQuery({
    queryKey: ['userThreads', username],
    queryFn:  () => threadsApi.getByUser(username).then(r => r.data),
    enabled:  !!username,
  })

  const openEdit = () => {
    setNewUsername(profile?.username ?? '')
    setNewBio(profile?.bio ?? '')
    setAvatarFile(null)
    setEditError('')
    setEditing(true)
  }

  const saveMut = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      if (newUsername && newUsername !== profile?.username) fd.append('username', newUsername)
      fd.append('bio', newBio)
      if (avatarFile) fd.append('file', avatarFile)
      return authApi.updateProfile(fd)
    },
    onSuccess: async () => {
      const fresh = await authApi.getProfile()
      setUser(fresh.data)
      const updatedUsername = fresh.data.username
      // Write fresh data directly into cache — no refetch, no undefined gap
      qc.setQueryData(['profile', updatedUsername], fresh.data)
      if (updatedUsername !== username) {
        navigate(`/profile/${updatedUsername}`, { replace: true })
      }
      setEditing(false)
    },
    onError: (e) => {
      setEditError(e?.response?.data?.detail ?? 'Update failed')
    },
  })

  const pwMut = useMutation({
    mutationFn: () => authApi.changePassword({ current_password: currentPw, new_password: newPw }),
    onSuccess: () => {
      setPwSuccess('Password changed successfully')
      setPwError('')
      setCurrentPw('')
      setNewPw('')
      setTimeout(() => { setChangingPw(false); setPwSuccess('') }, 1500)
    },
    onError: (e) => {
      setPwError(e?.response?.data?.detail ?? 'Password change failed')
      setPwSuccess('')
    },
  })

  if (isLoading) return <PageLayout><p className='text-sm text-gray-400'>Loading profile...</p></PageLayout>
  if (!profile)  return <PageLayout><p className='text-sm text-gray-400'>User not found.</p></PageLayout>

  return (
    <PageLayout>
      <div className='max-w-xl'>
        <div className='card mb-6'>
          <div className='flex items-start gap-5'>
            {/* Avatar */}
            <div className='w-20 h-20 rounded-full bg-blue-100 flex items-center justify-center
                            text-3xl font-semibold text-blue-700 flex-shrink-0 overflow-hidden'>
              {profile.avatar_url
                ? <img src={profile.avatar_url} alt={profile.username}
                    className='w-20 h-20 rounded-full object-cover' />
                : profile.username.slice(0, 2).toUpperCase()}
            </div>

            <div className='flex-1 min-w-0'>
              <div className='flex items-center gap-2'>
                <h1 className='text-xl font-semibold text-gray-900'>{profile.username}</h1>
                <span className='tag-pill capitalize'>{profile.role}</span>
                {isOwnProfile && (
                  <button onClick={openEdit}
                    className='ml-auto flex items-center gap-1 text-xs text-gray-500 border rounded-lg px-2 py-1 hover:bg-gray-50'>
                    <Pencil className='w-3 h-3' /> Edit profile
                  </button>
                )}
              </div>
              <p className='text-sm text-gray-500 mt-0.5'>{profile.email}</p>
              <p className='text-xs text-gray-400 mt-1'>
                Joined {formatDistanceToNow(new Date(profile.created_at), { addSuffix: true })}
              </p>
              {profile.bio && (
                <p className='mt-3 text-sm text-gray-700 leading-relaxed'>{profile.bio}</p>
              )}
              {!profile.bio && isOwnProfile && (
                <p className='mt-3 text-sm text-gray-400 italic'>No bio yet — click Edit profile to add one.</p>
              )}
            </div>
          </div>
        </div>

        {/* Change password */}
        {isOwnProfile && (
          <div className='card mb-6'>
            <div className='flex items-center justify-between'>
              <h2 className='text-sm font-semibold text-gray-700 flex items-center gap-1.5'>
                <Lock className='w-3.5 h-3.5' /> Password
              </h2>
              {!changingPw && (
                <button onClick={() => { setChangingPw(true); setPwError(''); setPwSuccess('') }}
                  className='text-xs text-gray-500 border rounded-lg px-2 py-1 hover:bg-gray-50'>
                  Change password
                </button>
              )}
            </div>
            {changingPw && (
              <div className='mt-4 space-y-3'>
                <div>
                  <label className='text-sm font-medium text-gray-700'>Current password</label>
                  <input type='password' value={currentPw} onChange={e => setCurrentPw(e.target.value)}
                    className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-light' />
                </div>
                <div>
                  <label className='text-sm font-medium text-gray-700'>New password (min 6 chars)</label>
                  <input type='password' value={newPw} onChange={e => setNewPw(e.target.value)}
                    className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-light' />
                </div>
                {pwError && <p className='text-sm text-red-500'>{pwError}</p>}
                {pwSuccess && <p className='text-sm text-green-600'>{pwSuccess}</p>}
                <div className='flex gap-2'>
                  <button onClick={() => pwMut.mutate()}
                    disabled={pwMut.isPending || !currentPw || newPw.length < 6}
                    className='px-4 py-2 text-sm bg-brand text-white rounded-lg hover:bg-brand-light disabled:opacity-50'>
                    {pwMut.isPending ? 'Saving...' : 'Update password'}
                  </button>
                  <button onClick={() => { setChangingPw(false); setPwError(''); setPwSuccess('') }}
                    className='px-4 py-2 text-sm border rounded-lg hover:bg-gray-50'>Cancel</button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* User's threads */}
        <h2 className='text-base font-semibold text-gray-900 mb-3'>
          {isOwnProfile ? 'Your threads' : `${profile.username}'s threads`}
        </h2>
        {userThreads?.threads?.length > 0 ? (
          <div className='space-y-3'>
            {userThreads.threads.map(t => (
              <ThreadCard key={t.id} thread={t} />
            ))}
          </div>
        ) : (
          <p className='text-sm text-gray-400'>No threads yet.</p>
        )}
      </div>

      {/* Edit modal */}
      {editing && (
        <div className='fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4'>
          <div className='bg-white rounded-2xl shadow-xl w-full max-w-md p-6'>
            <div className='flex items-center justify-between mb-5'>
              <h2 className='text-base font-semibold'>Edit profile</h2>
              <button onClick={() => setEditing(false)}><X className='w-4 h-4 text-gray-400' /></button>
            </div>

            <div className='space-y-4'>
              <div>
                <label className='text-sm font-medium text-gray-700'>Username</label>
                <input value={newUsername} onChange={e => setNewUsername(e.target.value)}
                  maxLength={20}
                  className='mt-1 w-full px-3 py-2 text-sm border rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-light' />
              </div>

              <div>
                <label className='text-sm font-medium text-gray-700'>Bio</label>
                <textarea value={newBio} onChange={e => setNewBio(e.target.value)}
                  rows={3} maxLength={300}
                  placeholder='Tell others about yourself...'
                  className='mt-1 w-full px-3 py-2 text-sm border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-brand-light' />
                <p className='text-xs text-gray-400 text-right'>{newBio.length}/300</p>
              </div>

              <div>
                <label className='text-sm font-medium text-gray-700'>Avatar</label>
                <input type='file' accept='image/*'
                  onChange={e => setAvatarFile(e.target.files?.[0] ?? null)}
                  className='mt-1 w-full text-sm text-gray-500 file:mr-3 file:py-1 file:px-3 file:rounded-lg file:border-0 file:text-xs file:bg-gray-100 file:text-gray-700' />
                {avatarFile && (
                  <img src={URL.createObjectURL(avatarFile)} alt='preview'
                    className='mt-2 w-16 h-16 rounded-full object-cover' />
                )}
              </div>

              {editError && <p className='text-sm text-red-500'>{editError}</p>}

              <div className='flex justify-end gap-3 pt-2'>
                <button onClick={() => setEditing(false)}
                  className='px-4 py-2 text-sm border rounded-lg hover:bg-gray-50'>Cancel</button>
                <button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}
                  className='px-4 py-2 text-sm bg-brand text-white rounded-lg hover:bg-brand-light disabled:opacity-50 transition'>
                  {saveMut.isPending ? 'Saving...' : 'Save changes'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </PageLayout>
  )
}
