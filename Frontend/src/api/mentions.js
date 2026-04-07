import { apiClient } from './client'

export const mentionsApi = {
  search: (q) => apiClient.get('/api/search/users', { params: { q, limit: 20 } }),
}
