/**
 * 班级管理API
 * ============
 * - getClassList(params): 分页查询班级列表
 * - createClass(data): 新增班级
 * - updateClass(id, data): 编辑班级
 * - deleteClass(id): 删除班级
 * - bindStudents(classId, studentIds): 批量关联学生
 * - unbindStudents(classId, studentIds): 批量移除学生
 */
import request from './request'

/**
 * 获取班级列表
 * @param {Object} params
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页条数
 * @param {string} params.grade - 年级筛选
 * @param {number} params.status - 状态筛选
 */
export function getClassList(params) {
  return request({
    url: '/classes',
    method: 'get',
    params
  })
}

/**
 * 获取班级详情
 * @param {number} id - 班级ID
 */
export function getClassDetail(id) {
  return request({
    url: `/classes/${id}`,
    method: 'get'
  })
}

/**
 * 新增班级
 * @param {Object} data
 * @param {string} data.grade - 年级
 * @param {string} data.name - 班级名称
 * @param {number} data.head_teacher_id - 班主任ID
 * @param {number} data.max_count - 最大人数
 */
export function createClass(data) {
  return request({
    url: '/classes',
    method: 'post',
    data
  })
}

/**
 * 更新班级信息
 * @param {number} id - 班级ID
 * @param {Object} data
 */
export function updateClass(id, data) {
  return request({
    url: `/classes/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除班级
 * @param {number} id - 班级ID
 */
export function deleteClass(id) {
  return request({
    url: `/classes/${id}`,
    method: 'delete'
  })
}

/**
 * 批量关联学生
 * @param {number} classId - 班级ID
 * @param {number[]} studentIds - 学生ID列表
 */
export function bindStudents(classId, studentIds) {
  return request({
    url: '/classes/bind-students',
    method: 'post',
    data: { class_id: classId, student_ids: studentIds }
  })
}

/**
 * 批量移除学生
 * @param {number} classId - 班级ID
 * @param {number[]} studentIds - 学生ID列表
 */
export function unbindStudents(classId, studentIds) {
  return request({
    url: '/classes/unbind-students',
    method: 'post',
    data: { class_id: classId, student_ids: studentIds }
  })
}
