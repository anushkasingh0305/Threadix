import { apiClient } from './client'

export const notifsApi = {
  getAll:      (params) => apiClient.get('/api/notifications/', { params }),
  unreadCount: () => apiClient.get('/api/notifications/unread-count'),
  markRead:    (id) => apiClient.patch(`/api/notifications/${id}/read`),
  markAllRead: () => apiClient.patch('/api/notifications/read-all'),
}
