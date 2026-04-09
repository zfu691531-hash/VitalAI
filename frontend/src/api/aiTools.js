import request from './request'

function aiRequest(url, data, timeout = 180000) {
  return request({
    url,
    method: 'post',
    data,
    timeout
  })
}

export function generateComment(data) {
  return aiRequest('/ai/comment', data)
}

export function generateDiscipline(data) {
  return aiRequest('/ai/discipline', data)
}

export function polishNotice(data) {
  return aiRequest('/ai/notice', data)
}

export function askRule(data) {
  return aiRequest('/ai/rule-qa', data, 120000)
}

export function diagnoseScore(data) {
  return aiRequest('/ai/score-diagnosis', data)
}

export function planMeeting(data) {
  return aiRequest('/ai/meeting', data)
}

export function mockInterview(data) {
  return aiRequest('/ai/interview', data)
}

export function generateGroup(data) {
  return aiRequest('/ai/group', data)
}

export function confirmGroupAssignment(data) {
  return aiRequest('/ai/group/confirm', data)
}
