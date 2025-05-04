import request from '../util/request'

// 视频跟踪相关 API
export function trackHistoryVideo (params) {
  return request({
    url: '/trackHistoryVideo',
    method: 'post',
    data: params,
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 停止目标跟踪
export function stopTrackingRequest () {
  return request({
    url: '/stopTrack',
    method: 'post',
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 轨迹可视化相关 API
export const filterRecords = (data) => {
  return request({
    method: 'post',
    url: '/filter',
    data: data
  })
}

export const analyzeSpacetimeConstraints = (data) => {
  return request({
    method: 'post',
    url: '/spatiotemporal',
    data: data
  })
}

export const extractFeatures = (data) => {
  return request({
    method: 'post',
    url: '/feature_extraction',
    data: data
  })
}

export const matchFeatures = (data) => {
  return request({
    method: 'post',
    url: '/feature_matching',
    data: data
  })
}

// 监控管理相关 API
export const getAllCameras = () => {
  return request({
    method: 'get',
    url: '/cameras'
  })
}

export const getCamera = (cameraId) => {
  return request({
    method: 'get',
    url: `/cameras/${cameraId}`
  })
}

export const addCamera = (data) => {
  return request({
    method: 'post',
    url: '/cameras',
    data: data
  })
}

export const updateCamera = (data) => {
  return request({
    method: 'put',
    url: `/cameras/${data.camera_id}`,
    data: data
  })
}

export const deleteCamera = (cameraId) => {
  return request({
    method: 'delete',
    url: `/cameras/${cameraId}`
  })
}

export const getCameraVideos = (cameraId, date) => {
  return request({
    method: 'get',
    url: `/cameras/${cameraId}/videos`,
    params: { date }
  })
}

export const addVideo = (data) => {
  return request({
    method: 'post',
    url: '/videos',
    data: data
  })
}

export const deleteVideo = (videoId) => {
  return request({
    method: 'delete',
    url: `/videos/${videoId}`
  })
}
