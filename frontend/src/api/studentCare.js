import request from './request'

export function getStudentCareProfile(studentId) {
  return request({
    url: `/student-care/profile/${studentId}`,
    method: 'get'
  })
}

export function getStudentCareSignals(studentId) {
  return request({
    url: `/student-care/signals/${studentId}`,
    method: 'get'
  })
}

export function getStudentCareAgentEval(studentId) {
  return request({
    url: `/student-care/agent-eval/${studentId}`,
    method: 'get',
    timeout: 120000
  })
}

export function getStudentCareIsolationBn(studentId) {
  return request({
    url: `/student-care/isolation-bn/${studentId}`,
    method: 'get'
  })
}

export function getStudentCareAgentHistory(studentId, params = {}) {
  return request({
    url: `/student-care/agent-eval-history/${studentId}`,
    method: 'get',
    params
  })
}

export function getStudentCareGraphHealth() {
  return request({
    url: '/student-care/graph-health',
    method: 'get'
  })
}

export function syncStudentCareGraph(studentId) {
  return request({
    url: `/student-care/graph-sync/${studentId}`,
    method: 'post'
  })
}

export function getStudentCareGraphView(studentId) {
  return request({
    url: `/student-care/graph-view/${studentId}`,
    method: 'get'
  })
}

export function confirmStudentCareAgentReview(recordId, data) {
  return request({
    url: `/student-care/agent-eval-review/${recordId}`,
    method: 'post',
    data
  })
}

export function getStudentCareAgentStats(params = {}) {
  return request({
    url: '/student-care/agent-stats',
    method: 'get',
    params
  })
}

export function getStudentCareEvaluationSummary(params = {}) {
  return request({
    url: '/student-care/evaluation-summary',
    method: 'get',
    params
  })
}

export function getStudentCareEvaluationDetail(params = {}) {
  return request({
    url: '/student-care/evaluation-detail',
    method: 'get',
    params
  })
}

export function exportStudentCareAgentStats(params = {}) {
  return request({
    url: '/student-care/agent-stats-export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

export function exportStudentCareEvaluationSummary(params = {}) {
  return request({
    url: '/student-care/evaluation-summary-export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}
