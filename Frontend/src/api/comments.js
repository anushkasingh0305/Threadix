import { apiClient } from './client'

export const commentsApi = {
  getTopLevel: (threadId, params) =>
    apiClient.get(`/api/threads/${threadId}/comments/`, { params }),

  getChildren: (threadId, commentId, params) =>
    apiClient.get(`/api/threads/${threadId}/comments/${commentId}/children`, { params }),

  create: (threadId, data) =>
    apiClient.post(`/api/threads/${threadId}/comments/`, data),

  update: (threadId, commentId, data) =>
    apiClient.patch(`/api/threads/${threadId}/comments/${commentId}`, data),

  delete: (threadId, commentId) =>
    apiClient.delete(`/api/threads/${threadId}/comments/${commentId}`),

  toggleLike: (threadId, commentId) =>
    apiClient.post(`/api/threads/${threadId}/comments/${commentId}/like`),
}
