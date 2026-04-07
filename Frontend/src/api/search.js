import { apiClient } from './client'

export const searchApi = {
  threads: (q, params) =>
    apiClient.get('/api/search/threads', { params: { q, ...params } }),
}
