import axios from 'axios'
import { ElMessage } from 'element-plus'

import router from '@/router'
import { useUserStore } from '@/stores/user'
import { getToken } from '@/utils/auth'

const service = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

function cleanParams(value) {
  if (Array.isArray(value)) {
    return value
      .map((item) => cleanParams(item))
      .filter((item) => item !== undefined)
  }

  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value)
        .map(([key, item]) => [key, cleanParams(item)])
        .filter(([, item]) => item !== undefined)
    )
  }

  if (value === '' || value === null || value === undefined) {
    return undefined
  }

  return value
}

service.interceptors.request.use(
  (config) => {
    const token = getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    if (config.params) {
      config.params = cleanParams(config.params)
    }
    return config
  },
  (error) => Promise.reject(error)
)

service.interceptors.response.use(
  (response) => {
    if (response.config.responseType === 'blob') {
      return response.data
    }

    const res = response.data

    // Compatibility for auth/login which returns raw token payload.
    if (res && typeof res === 'object' && 'access_token' in res && 'token_type' in res) {
      return res
    }

    if (!res || typeof res !== 'object' || !('code' in res)) {
      return res
    }

    if (res.code !== 200) {
      ElMessage.error(res.msg || '请求失败')

      if (res.code === 401) {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
      }

      return Promise.reject(new Error(res.msg || '请求失败'))
    }

    return res.data
  },
  (error) => {
    if (error.response) {
      const status = error.response.status
      const msg = error.response.data?.msg || error.response.data?.detail || '请求失败'

      switch (status) {
        case 401: {
          ElMessage.error('登录已过期，请重新登录')
          const userStore = useUserStore()
          userStore.logout()
          router.push('/login')
          break
        }
        case 403:
          ElMessage.error('没有权限访问')
          break
        case 404:
          ElMessage.error('请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(msg)
      }
    } else if (error.message?.includes('timeout')) {
      ElMessage.error('请求超时，请检查网络')
    } else if (error.message?.includes('Network Error')) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error(error.message || '未知错误')
    }

    return Promise.reject(error)
  }
)

export default service
