import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import Function from '../views/Function.vue'
import TrackVisualization from '../views/TrackVisualization'
import CameraManagement from '../views/CameraManagement'
import StudentManagement from '../views/StudentManagement.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    name: 'Home',
    component: HomeView,
    meta: { requiresAuth: false }
  },
  {
    path: '/Function',
    name: 'Function',
    component: Function,
    meta: { requiresAuth: true }
  },
  {
    path: '/StudentManagement',
    name: 'StudentManagement',
    component: StudentManagement,
    meta: { requiresAuth: true }
  },
  {
    path: '/TrackVisualization',
    name: 'TrackVisualization',
    component: TrackVisualization,
    meta: { requiresAuth: true }
  },
  {
    path: '/CameraManagement',
    name: 'CameraManagement',
    component: CameraManagement,
    meta: { requiresAuth: true }
  }
]

const router = new VueRouter({
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  if (to.matched.some(record => record.meta.requiresAuth)) {
    // 需要认证的页面
    if (!token) {
      next({
        path: '/home',
        query: { redirect: to.fullPath }
      })
    } else {
      next()
    }
  } else {
    // 不需要认证的页面
    next()
  }
})

export default router
