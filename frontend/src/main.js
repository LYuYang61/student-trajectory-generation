import Vue from 'vue'
import App from './App.vue'
import router from './router'
import store from './store'

import ElementUI from 'element-ui'
import 'element-ui/lib/theme-chalk/index.css'
import http from './util/http'

import {VUE_SOCKET_IO} from './util/socket'

import './static/css/common.css'

// import videoPlay from 'vue3-video-play' // 引入组件
// import 'vue3-video-play/dist/style.css' // 引入css
// app.use(videoPlay)
Vue.use(ElementUI)
Vue.use(VUE_SOCKET_IO)

Vue.config.productionTip = false
Vue.prototype.$http = http

new Vue({
  router,
  store,
  render: h => h(App)
}).$mount('#app')
