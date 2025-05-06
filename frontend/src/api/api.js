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

// 打开包含视频文件的文件夹
export function openFolder (path) {
  return request({
    url: '/openFolder',
    method: 'post',
    data: { path },
    headers: {
      'Content-Type': 'application/json'
    }
  })
}

// 在本地播放器中播放视频
export function playInLocalPlayer (path) {
  return request({
    url: '/playInLocalPlayer',
    method: 'post',
    data: { path },
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

// Add these functions to your existing api.js file

// 获取学生列表（支持分页）
export const getStudents = (params) => {
  return request({
    method: 'get',
    url: '/students',
    params: params
  })
}

// 搜索学生
export const searchStudents = (params) => {
  return request({
    method: 'get',
    url: '/students/search',
    params: params
  })
}

// 添加单个学生
export const addStudent = (data) => {
  return request({
    method: 'post',
    url: '/students',
    data: data
  })
}

// 更新学生信息
export const updateStudent = (data) => {
  return request({
    method: 'put',
    url: `/students/${data.student_id}`,
    data: data
  })
}

// 删除单个学生
export const deleteStudent = (studentId) => {
  return request({
    method: 'delete',
    url: `/students/${studentId}`
  })
}

// 批量删除学生
export const batchDeleteStudents = (data) => {
  return request({
    method: 'post',
    url: '/students/batch-delete',
    data: data
  })
}

// 从Excel导入学生
export const importStudentsFromExcel = (data) => {
  return request({
    method: 'post',
    url: '/students/import',
    data: data
  })
}
