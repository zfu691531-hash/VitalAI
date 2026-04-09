/**
 * Token存储工具
 * ==============
 * - getToken(): 从localStorage读取JWT token
 * - setToken(token): 保存token到localStorage
 * - removeToken(): 清除token（退出登录时调用）
 */

const TOKEN_KEY = 'aistu_token'

/**
 * 获取Token
 * @returns {string} token
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || ''
}

/**
 * 设置Token
 * @param {string} token
 */
export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

/**
 * 移除Token
 */
export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}
