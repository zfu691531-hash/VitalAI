import request from './request'

export function getSchoolRuleList(params) {
  return request({
    url: '/school-rules',
    method: 'get',
    params
  })
}

export function getSchoolRuleCategories() {
  return request({
    url: '/school-rules/categories',
    method: 'get'
  })
}

export function createSchoolRule(data) {
  return request({
    url: '/school-rules',
    method: 'post',
    data
  })
}

export function updateSchoolRule(id, data) {
  return request({
    url: `/school-rules/${id}`,
    method: 'put',
    data
  })
}

export function deleteSchoolRule(id) {
  return request({
    url: `/school-rules/${id}`,
    method: 'delete'
  })
}
