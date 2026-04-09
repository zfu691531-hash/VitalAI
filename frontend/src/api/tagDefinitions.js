import request from './request'

export function getTagDefinitions(params = {}) {
  return request({
    url: '/tag-definitions',
    method: 'get',
    params
  })
}

export function createTagDefinition(data) {
  return request({
    url: '/tag-definitions',
    method: 'post',
    data
  })
}

export function updateTagDefinition(id, data) {
  return request({
    url: `/tag-definitions/${id}`,
    method: 'put',
    data
  })
}

export function deleteTagDefinition(id) {
  return request({
    url: `/tag-definitions/${id}`,
    method: 'delete'
  })
}

export function getAvailableTagDefinitions(params = {}) {
  return request({
    url: '/tag-definitions/available',
    method: 'get',
    params
  })
}
