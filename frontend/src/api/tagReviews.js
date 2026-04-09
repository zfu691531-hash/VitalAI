import request from './request'

export const getTagReviews = (params) => request.get('/api/tag-reviews', { params })

export const approveTagReview = (id, data) => request.post(`/api/tag-reviews/${id}/approve`, data)

export const rejectTagReview = (id, data) => request.post(`/api/tag-reviews/${id}/reject`, data)
