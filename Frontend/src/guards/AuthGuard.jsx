import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

export function AuthGuard() {
  const isAuthed = useAuthStore((s) => s.isAuthed)
  return isAuthed ? <Outlet /> : <Navigate to='/login' replace />
}
