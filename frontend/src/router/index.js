import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView.vue'
import Function from '../views/Function.vue'
import TrackVisualization from '../views/TrackVisualization'
import CameraManagement from '../views/CameraManagement'
import StudentManagement from '../views/StudentManagement.vue'
import ProfileView from '../views/ProfileView.vue'

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
    path: '/profile',
    name: 'profile',
    component: ProfileView,
    meta: { requiresAuth: true }
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
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  if (to.matched.some(record => record.meta.requiresAuth)) {
    const token = localStorage.getItem('token')
    if (!token) {
      next({
        path: '/',
        query: { redirect: to.fullPath }
      })
    } else {
      next()
    }
  } else {
    next()
  }
})

export default router
