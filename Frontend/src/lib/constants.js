export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'
export const WS_BASE  = API_BASE.replace('http', 'ws')

export const ROLES = {
  ADMIN:     'admin',
  MODERATOR: 'moderator',
  MEMBER:    'member',
}

export const MAX_COMMENT_DEPTH = 4
export const PAGE_SIZE = 20
