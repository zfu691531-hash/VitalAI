import request from './request'

export function getAttendance(params) {
  return request({
    url: '/attendance',
    method: 'get',
    params
  })
}

export function createAttendance(data) {
  return request({
    url: '/attendance',
    method: 'post',
    data
  })
}

export function updateAttendance(id, data) {
  return request({
    url: `/attendance/${id}`,
    method: 'put',
    data
  })
}

export function deleteAttendance(id) {
  return request({
    url: `/attendance/${id}`,
    method: 'delete'
  })
}

export function getBehaviorEvents(params) {
  return request({
    url: '/behavior-events',
    method: 'get',
    params
  })
}

export function createBehaviorEvent(data) {
  return request({
    url: '/behavior-events',
    method: 'post',
    data
  })
}

export function updateBehaviorEvent(id, data) {
  return request({
    url: `/behavior-events/${id}`,
    method: 'put',
    data
  })
}

export function deleteBehaviorEvent(id) {
  return request({
    url: `/behavior-events/${id}`,
    method: 'delete'
  })
}

export function getCareObservations(params) {
  return request({
    url: '/care-observations',
    method: 'get',
    params
  })
}

export function createCareObservation(data) {
  return request({
    url: '/care-observations',
    method: 'post',
    data
  })
}

export function updateCareObservation(id, data) {
  return request({
    url: `/care-observations/${id}`,
    method: 'put',
    data
  })
}

export function deleteCareObservation(id) {
  return request({
    url: `/care-observations/${id}`,
    method: 'delete'
  })
}

export function getFamilyContacts(params) {
  return request({
    url: '/family-contacts',
    method: 'get',
    params
  })
}

export function createFamilyContact(data) {
  return request({
    url: '/family-contacts',
    method: 'post',
    data
  })
}

export function deleteFamilyContact(id) {
  return request({
    url: `/family-contacts/${id}`,
    method: 'delete'
  })
}

export function getAssistantSummaries(params) {
  return request({
    url: '/assistant-summary',
    method: 'get',
    params
  })
}

export function createAssistantSummary(data) {
  return request({
    url: '/assistant-summary',
    method: 'post',
    data
  })
}

export function getGraphRelations(params) {
  return request({
    url: '/graph-relations',
    method: 'get',
    params
  })
}

export function createGraphRelation(data) {
  return request({
    url: '/graph-relations',
    method: 'post',
    data
  })
}

export function updateGraphRelation(id, data) {
  return request({
    url: `/graph-relations/${id}`,
    method: 'put',
    data
  })
}

export function deleteGraphRelation(id) {
  return request({
    url: `/graph-relations/${id}`,
    method: 'delete'
  })
}
