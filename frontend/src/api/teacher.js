import request from './request'

export function getTeacherList(params) {
  return request({
    url: '/teachers',
    method: 'get',
    params
  })
}

export function createTeacher(data) {
  return request({
    url: '/teachers',
    method: 'post',
    data
  })
}

export function updateTeacher(id, data) {
  return request({
    url: `/teachers/${id}`,
    method: 'put',
    data
  })
}

export function deleteTeacher(id) {
  return request({
    url: `/teachers/${id}`,
    method: 'delete'
  })
}

export function bindTeacherClasses(teacherId, classIds) {
  return request({
    url: '/teachers/bind-classes',
    method: 'post',
    data: { teacher_id: teacherId, class_ids: classIds }
  })
}

export function unbindTeacherClasses(teacherId, classIds) {
  return request({
    url: '/teachers/unbind-classes',
    method: 'post',
    data: { teacher_id: teacherId, class_ids: classIds }
  })
}
