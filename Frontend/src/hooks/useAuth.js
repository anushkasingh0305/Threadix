import { useAuthStore } from '@/store/authStore'
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export function useAuth(redirectIfUnauthed = false) {
  const { user, isAuthed } = useAuthStore()
  const navigate = useNavigate()
  useEffect(() => {
    if (redirectIfUnauthed && !isAuthed) navigate('/login')
  }, [isAuthed, redirectIfUnauthed, navigate])
  return { user, isAuthed }
}
