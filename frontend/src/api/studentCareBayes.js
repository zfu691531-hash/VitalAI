import request from './request'

export function getStudentCareBayesRules() {
  return request({
    url: '/student-care/bayes-rules',
    method: 'get'
  })
}

export function updateStudentCareBayesRule(dimension, evidenceKey, data) {
  return request({
    url: `/student-care/bayes-rules/${dimension}/${encodeURIComponent(evidenceKey)}`,
    method: 'put',
    data
  })
}
