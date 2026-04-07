import axios from 'axios'
import { API_BASE } from '@/lib/constants'

export const apiClient = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// Auto-refresh access token on 401, then retry the original request
apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    if (err.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        await apiClient.post('/api/auth/auth/refresh')
        return apiClient(original)
      } catch {
        localStorage.removeItem('threadix-auth')
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)
