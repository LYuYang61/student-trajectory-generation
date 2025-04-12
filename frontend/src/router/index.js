import Vue from 'vue'
import VueRouter from 'vue-router'
import HomeView from '../views/HomeView'
import Tracking from '../views/Tracking'
import TrackByVideo from '../views/TrackByVideo'
import RealtimeTracking from '../views/RealtimeTracking'
import TrackVisualization from '../views/TrackVisualization'

Vue.use(VueRouter)

const routes = [
  {
    path: '/',
    name: 'home',
    component: HomeView
  },
  {
    path: '/Tracking',
    name: 'Tracking',
    component: Tracking
  },
  {
    path: '/TrackByVideo',
    name: 'TrackByVideo',
    component: TrackByVideo
  },
  {
    path: '/RealtimeTracking',
    name: 'RealtimeTracking',
    component: RealtimeTracking
  },
  {
    path: '/TrackVisualization',
    name: 'TrackVisualization',
    component: TrackVisualization
  }
]

const router = new VueRouter({
  routes
})

export default router
