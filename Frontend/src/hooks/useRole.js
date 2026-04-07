import { useAuthStore } from '@/store/authStore'

export function useRole() {
  const role = useAuthStore((s) => s.user?.role ?? 'member')
  return {
    isAdmin:     role === 'admin',
    isModerator: role === 'moderator' || role === 'admin',
    isMember:    true,
    role,
  }
}
