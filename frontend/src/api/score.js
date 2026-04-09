import request from './request'

export function getScoreList(params) {
  return request({
    url: '/scores',
    method: 'get',
    params
  })
}

export function getScoreStats(params) {
  return request({
    url: '/scores/stats',
    method: 'get',
    params
  })
}

export function createScore(data) {
  return request({
    url: '/scores',
    method: 'post',
    data
  })
}

export function updateScore(id, data) {
  return request({
    url: `/scores/${id}`,
    method: 'put',
    data
  })
}

export function deleteScore(id) {
  return request({
    url: `/scores/${id}`,
    method: 'delete'
  })
}

export function batchDeleteScores(ids) {
  return request({
    url: '/scores/batch',
    method: 'delete',
    data: { ids }
  })
}

export function importScores(file) {
  const formData = new FormData()
  formData.append('file', file)

  return request({
    url: '/scores/import',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function exportScores(params) {
  return request({
    url: '/scores/export',
    method: 'get',
    params,
    responseType: 'blob'
  })
}

export function downloadScoreTemplate() {
  return request({
    url: '/scores/template',
    method: 'get',
    responseType: 'blob'
  })
}
