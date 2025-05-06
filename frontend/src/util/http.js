import axios from 'axios'
import router from '../router'
import { Message } from 'element-ui'

// 创建 axios 实例
const http = axios.create({
  baseURL: process.env.VUE_APP_API_URL || '/api',
  timeout: 10000
})

// 请求拦截器
http.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  response => {
    return response
  },
  error => {
    if (error.response) {
      if (error.response.status === 401) {
        // 401 未授权，token 过期或无效
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        Message.error('登录已过期，请重新登录')
        router.push('/login')
      } else if (error.response.status === 403) {
        // 403 禁止访问
        Message.error('没有权限访问此资源')
      } else if (error.response.status === 404) {
        // 404 资源不存在
        Message.error('请求的资源不存在')
      } else {
        // 其他错误
        Message.error(error.response.data.message || '请求失败')
      }
    } else {
      Message.error('网络错误，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default http
