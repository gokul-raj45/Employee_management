import axios from 'axios'

// Backend URL comes from frontend/.env (VITE_API_BASE_URL); never hardcode it in components.
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:5000').replace(/\/$/, '')
export const TOKEN_KEY = 'hr_token'
export const USER_KEY = 'hr_user'
export const AUTH_EXPIRED_EVENT = 'hr:auth-expired'

const api = axios.create({ baseURL: API_BASE_URL, timeout: 15000 })

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired/invalid token on a protected call logs the user out (but a wrong password on /api/login must not).
    const isLogin = error.config?.url?.includes('/api/login')
    if (error.response?.status === 401 && !isLogin) window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT))
    return Promise.reject(error)
  },
)

/** Turn any axios error into a readable message for the UI. */
export function errorMessage(error) {
  if (error.response) return error.response.data?.error || `Request failed (${error.response.status})`
  if (error.code === 'ECONNABORTED') return 'The server took too long to respond.'
  return `Cannot reach the server at ${API_BASE_URL}. Is the backend running, and is CORS configured for this page's address?`
}

export default api
