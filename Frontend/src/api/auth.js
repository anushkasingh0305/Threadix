import { apiClient } from './client'

export const authApi = {
  register: (data) =>
    apiClient.post('/api/auth/auth/register', data),

  login: (data) =>
    apiClient.post('/api/auth/auth/login', data),

  logout: () => apiClient.post('/api/auth/auth/logout'),

  getProfile: () => apiClient.get('/api/auth/user/profile'),

  updateProfile: (data) =>
    apiClient.put('/api/auth/user/profile', data, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  changePassword: (data) =>
    apiClient.put('/api/auth/user/change-password', data),

  resetPassword: (token, new_password) =>
    apiClient.post('/api/auth/auth/reset-password', { token, new_password }),
}
