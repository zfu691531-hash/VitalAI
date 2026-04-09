/**
 * 用户状态管理（Pinia Store）
 * ============================
 * 存储当前登录用户的认证信息与权限数据：
 * - token: JWT令牌
 * - userInfo: 用户基本信息（id、姓名、角色）
 * - isLoggedIn: 登录状态计算属性
 * - login/logout: 登录登出动作
 * - setToken: 设置token（供request.js拦截器使用）
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getToken, setToken as saveToken, removeToken } from '@/utils/auth'
import { login as loginApi, getUserInfo } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  // 状态
  const token = ref(getToken() || '')
  const userInfo = ref(null)

  // 计算属性：是否已登录
  const isLoggedIn = computed(() => !!token.value)

  // 计算属性：用户角色
  const role = computed(() => userInfo.value?.role || '')

  // 计算属性：用户名
  const username = computed(() => userInfo.value?.username || '')

  // 计算属性：姓名
  const name = computed(() => userInfo.value?.name || '')

  /**
   * 登录
   * @param {string} username 用户名
   * @param {string} password 密码
   * @returns {Promise}
   */
  async function login(username, password) {
    try {
      const authData = await loginApi({ username, password })
      const { access_token } = authData

      // 保存token
      token.value = access_token
      saveToken(access_token)

      // 获取用户信息
      await fetchUserInfo()

      return authData
    } catch (error) {
      throw error
    }
  }

  /**
   * 获取用户信息
   */
  async function fetchUserInfo() {
    try {
      const userData = await getUserInfo()
      userInfo.value = userData
      return userData
    } catch (error) {
      throw error
    }
  }

  /**
   * 登出
   */
  function logout() {
    token.value = ''
    userInfo.value = null
    removeToken()
    router.push('/login')
  }

  /**
   * 设置token（供外部调用）
   */
  function setToken(newToken) {
    token.value = newToken
    saveToken(newToken)
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    role,
    username,
    name,
    login,
    logout,
    fetchUserInfo,
    setToken
  }
})
