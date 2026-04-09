/**
 * 学生管理API
 * ============
 * - getStudentList(params): 分页查询学生列表
 * - createStudent(data): 新增学生
 * - updateStudent(id, data): 编辑学生
 * - deleteStudent(id): 删除学生
 * - batchDeleteStudents(ids): 批量删除学生
 * - importStudents(file): 批量导入学生（Excel）
 * - exportStudents(params): 批量导出学生（Excel）
 * - downloadStudentTemplate(): 下载导入模板
 */
import request from './request'

/**
 * 获取学生列表
 * @param {Object} params
 * @param {number} params.page - 页码
 * @param {number} params.page_size - 每页条数
 * @param {string} params.keyword - 关键词搜索
 * @param {number} params.class_id - 班级ID
 * @param {string} params.tag - 标签筛选
 * @param {string} params.gender - 性别筛选
 */
export function getStudentList(params) {
  return request({
    url: '/students',
    method: 'get',
    params
  })
}

/**
 * 获取学生详情
 * @param {number} id - 学生ID
 */
export function getStudentDetail(id) {
  return request({
    url: `/students/${id}`,
    method: 'get'
  })
}

/**
 * 新增学生
 * @param {Object} data
 * @param {string} data.student_no - 学号
 * @param {string} data.name - 姓名
 * @param {string} data.gender - 性别 male/female
 * @param {number} data.age - 年龄
 * @param {number} data.class_id - 班级ID
 * @param {string} data.contact - 联系方式
 * @param {string} data.specialty - 特长
 * @param {string} data.tags - 标签（逗号分隔）
 */
export function createStudent(data) {
  return request({
    url: '/students',
    method: 'post',
    data
  })
}

/**
 * 更新学生信息
 * @param {number} id - 学生ID
 * @param {Object} data
 */
export function updateStudent(id, data) {
  return request({
    url: `/students/${id}`,
    method: 'put',
    data
  })
}

/**
 * 删除学生
 * @param {number} id - 学生ID
 */
export function deleteStudent(id) {
  return request({
    url: `/students/${id}`,
    method: 'delete'
  })
}

/**
 * 批量删除学生
 * @param {number[]} ids - 学生ID列表
 */
export function batchDeleteStudents(ids) {
  return request({
    url: '/students/batch',
    method: 'delete',
    data: { ids }
  })
}

/**
 * 导入学生
 * @param {File} file - Excel文件
 */
export function importStudents(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: '/students/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 导出学生
 * @param {Object} params - 筛选参数
 */
export function exportStudents(params) {
  return request({
    url: '/students/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

/**
 * 下载导入模板
 */
export function downloadStudentTemplate() {
  return request({
    url: '/students/template',
    method: 'get',
    responseType: 'blob'
  })
}
