import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView'
import Function from '../views/Function.vue'
import TrackByVideo from '../views/TrackByVideo'
import TrackVisualization from '../views/TrackVisualization'
import CameraManagement from '../views/CameraManagement'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/Function',
    name: 'Function',
    component: Function
  },
  {
    path: '/TrackByVideo',
    name: 'TrackByVideo',
    component: TrackByVideo
  },
  {
    path: '/TrackVisualization',
    name: 'TrackVisualization',
    component: TrackVisualization
  },
  {
    path: '/CameraManagement',
    name: 'CameraManagement',
    component: CameraManagement
  }
]

const router = new VueRouter({
  routes
})

export default router
