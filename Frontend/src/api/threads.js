import { apiClient } from './client'

export const threadsApi = {
  getFeed: (params) =>
    apiClient.get('/api/threads/feed', { params }),

  getAll: (params) =>
    apiClient.get('/api/threads/', { params }),

  getByUser: (username, params) =>
    apiClient.get(`/api/threads/user/${username}`, { params }),

  getOne: (id) => apiClient.get(`/api/threads/${id}`),

  create: (data) =>
    apiClient.post('/api/threads/', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  update: (id, data) =>
    apiClient.patch(`/api/threads/${id}`, data),

  delete: (id) => apiClient.delete(`/api/threads/${id}`),

  toggleLike: (id) => apiClient.post(`/api/threads/${id}/like`),
}
