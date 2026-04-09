import request from './request'

export function getAiHistoryList(params) {
  return request({
    url: '/ai-history',
    method: 'get',
    params
  })
}

export function getAiHistoryDetail(id) {
  return request({
    url: `/ai-history/${id}`,
    method: 'get'
  })
}

export function deleteAiHistory(id) {
  return request({
    url: '/ai-history/batch-delete',
    method: 'post',
    data: { ids: [id] }
  })
}

export function batchDeleteAiHistory(ids) {
  return request({
    url: '/ai-history/batch-delete',
    method: 'post',
    data: { ids }
  })
}
