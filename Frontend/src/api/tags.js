import { apiClient } from './client'

export const tagsApi = {
  getAll: () => apiClient.get('/api/tags/'),
  create: (name) => apiClient.post('/api/tags/', { name }),
}
