import request from './request'

export function askRuleRag(data) {
  return request({
    url: '/rule-rag/ask',
    method: 'post',
    data
  })
}

export function submitRuleRagFeedback(data) {
  return request({
    url: '/rule-rag/feedback',
    method: 'post',
    data
  })
}

export function getRuleRagHistory(params) {
  return request({
    url: '/rule-rag/history',
    method: 'get',
    params
  })
}
