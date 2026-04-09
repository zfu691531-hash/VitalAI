/**
 * 认证API
 * ========
 * - login(username, password): 用户登录
 * - getUserInfo(): 获取当前用户信息
 */
import request from './request'

/**
 * 用户登录
 * @param {Object} data - 登录信息
 * @param {string} data.username - 用户名
 * @param {string} data.password - 密码
 * @returns {Promise}
 */
export function login(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

/**
 * 获取当前用户信息
 * @returns {Promise}
 */
export function getUserInfo() {
  return request({
    url: '/users/me',
    method: 'get'
  })
}

/**
 * 修改密码
 * @param {Object} data
 * @param {string} data.old_password - 旧密码
 * @param {string} data.new_password - 新密码
 * @returns {Promise}
 */
export function changePassword(data) {
  return request({
    url: '/users/me/password',
    method: 'put',
    data
  })
}

/**
 * 更新用户信息
 * @param {Object} data
 * @param {string} data.name - 姓名
 * @returns {Promise}
 */
export function updateUserInfo(data) {
  return request({
    url: '/users/me',
    method: 'put',
    data
  })
}
