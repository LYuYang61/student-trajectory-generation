<template>
  <div>
    <!-- 首页时只显示一个按钮 -->
    <div v-if="$route.path === '/'" class="home-menu">
      <img class="logo" src="../assets/hfut.png" alt=""/>
      <el-button type="primary" class="enter-btn" @click="enterSystem">
        <span>点击进入</span>
      </el-button>
    </div>

    <!-- 非首页时显示完整菜单 -->
    <el-menu
      v-else
      :default-active="$route.path"
      class="el-menu-demo"
      mode="horizontal"
      router>
      <img class="logo" src="../assets/hfut.png" alt=""/>
      <el-menu-item v-for="page in pages"
                    :key="page.index"
                    :index="page.index">
        {{ page.name }}
      </el-menu-item>

      <!-- 返回首页按钮 -->
      <el-button type="primary" class="home-btn" @click="goHome">
        <span>返回首页</span>
      </el-button>
    </el-menu>
  </div>
</template>

<script>
export default {
  name: 'Menu',
  data () {
    return {
      pages: [
        {name: '功能介绍', index: '/Function'},
        {name: '监控管理', index: '/CameraManagement'},
        {name: '视频跟踪', index: '/TrackByVideo'},
        {name: '轨迹可视化', index: '/TrackVisualization'}
      ]
    }
  },
  methods: {
    enterSystem () {
      this.$router.push('/Function')
    },
    goHome () {
      this.$router.push('/')
    }
  }
}
</script>

<style scoped>
.logo {
  float: left;
  margin: 1% 3%;
  width: 100px;
  height: 100px;
}

.el-menu {
  border-bottom: none !important;
  background-color: rgba(0, 0, 0, 0.525);
  /* margin-right: 3%; */
  position: relative;
}

.el-menu--horizontal > .el-menu-item {
  margin: 2% 0;
  text-align: center;
  line-height: 9vh;
  display: inline-block;
  font-size: 1.5vw;
  color: #dddddd;
  border-bottom: none;
  border-radius: 8px;
}

.el-menu--horizontal > .el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.775);
  color: #4d86ff;
  border-radius: 8px;
}

.el-menu--horizontal > .el-menu-item.is-active {
  border-bottom: none;
  color: #4d86ff;
}

/* 首页菜单样式 */
.home-menu {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 3%;
  background-color: rgba(0, 0, 0, 0.525);
  height: 135px;
}

.enter-btn {
  position: absolute;
  right: 3%;
  font-size: 1.2vw;
  padding: 10px 20px;
  border-radius: 8px;
}

/* 返回首页按钮样式 */
.home-btn {
  position: absolute;
  right: 3%;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.2vw;
  padding: 10px 20px;
  border-radius: 8px;
}
</style>
