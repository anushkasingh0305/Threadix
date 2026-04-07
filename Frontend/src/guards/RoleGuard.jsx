import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

const HIERARCHY = { member: 0, moderator: 1, admin: 2 }

export function RoleGuard({ minRole }) {
  const role = useAuthStore((s) => s.user?.role ?? 'member')
  return HIERARCHY[role] >= HIERARCHY[minRole]
    ? <Outlet />
    : <Navigate to='/feed' replace />
}
