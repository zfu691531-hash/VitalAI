import request from './request'

export function getRuleFeedbackList(params) {
  return request({
    url: '/rule-feedback',
    method: 'get',
    params
  })
}

export function getRuleFeedbackDetail(id) {
  return request({
    url: `/rule-feedback/${id}`,
    method: 'get'
  })
}

export function adoptRuleFeedback(id, data) {
  return request({
    url: `/rule-feedback/${id}/adopt`,
    method: 'post',
    data
  })
}

export function reviseAndAdoptRuleFeedback(id, data) {
  return request({
    url: `/rule-feedback/${id}/revise-and-adopt`,
    method: 'post',
    data
  })
}

export function rejectRuleFeedback(id, data) {
  return request({
    url: `/rule-feedback/${id}/reject`,
    method: 'post',
    data
  })
}
