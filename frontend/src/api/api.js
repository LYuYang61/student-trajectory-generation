// import axios from 'axios'
// import {SERVER_ADDRESS} from '../static/js/global'
//
// export const trackByImg = (data) => {
//   return axios({
//     method: 'post',
//     url: `${SERVER_ADDRESS}/trackByImg`,
//     responseType: 'blob',
//     data: data
//   })
// }
//
// export const trackByVideo = (data) => {
//   return axios({
//     method: 'post',
//     url: `${SERVER_ADDRESS}/trackByVideo`,
//     responseType: 'blob',
//     data: data
//   })
// }
//
// export const cancelTrack = () => {
//   return axios({
//     method: 'get',
//     url: `${SERVER_ADDRESS}/cancelTrack`
//   })
// }
//
// export const realtimeTrackType = (data) => {
//   return axios({
//     method: 'post',
//     url: `${SERVER_ADDRESS}/realtimeTrackType`,
//     data: data
//   })
// }
//
import request from '../util/request'

export const trackByVideo = (data) => {
  return request({
    method: 'post',
    url: '/trackByVideo',
    data: data
  })
}

export const realtimeTrackType = (data) => {
  return request({
    method: 'post',
    url: '/realtimeTrackType',
    data: data
  })
}

export const stopDetection = () => {
  return request({
    method: 'post',
    url: '/stopDetection'
  })
}

// 添加轨迹可视化相关API
export const filterRecords = (data) => {
  return request({
    method: 'post',
    url: '/api/filter',
    data: data
  })
}

export const analyzeSpacetimeConstraints = (data) => {
  return request({
    method: 'post',
    url: '/api/spatiotemporal',
    data: data
  })
}

export const performReID = (data) => {
  return request({
    method: 'post',
    url: '/api/reid',
    data: data
  })
}

export const getTrajectory = (data) => {
  return request({
    method: 'post',
    url: '/api/trajectory',
    data: data
  })
}
// export const test = () => {
//   return request({
//     method: 'get',
//     url: '/test'
//   })
// }
