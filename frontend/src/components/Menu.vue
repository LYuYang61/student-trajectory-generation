<template>
  <div>
    <!-- 首页时显示简化版菜单 -->
    <div v-if="$route.path === '/home' || $route.path === '/'" class="home-menu">
      <img class="logo" src="../assets/hfut.png" alt=""/>
    </div>

    <!-- 非首页且已登录时显示完整菜单 -->
    <el-menu
      v-else-if="isLoggedIn"
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

      <div class="menu-right">
        <el-dropdown @command="handleCommand" v-if="isLoggedIn">
          <span class="el-dropdown-link">
            {{ username }}<i class="el-icon-arrow-down el-icon--right"></i>
          </span>
          <el-dropdown-menu slot="dropdown">
            <el-dropdown-item command="profile">个人信息</el-dropdown-item>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </el-dropdown>
        <el-button v-else type="text" @click="$emit('login')">登录</el-button>
      </div>
    </el-menu>

    <!-- 非首页但未登录时显示仅有logo的菜单 -->
    <div v-else class="simple-menu">
      <img class="logo" src="../assets/hfut.png" alt=""/>
    </div>
  </div>
</template>

<script>
// 保持原有脚本不变
export default {
  name: 'Menu',
  data () {
    return {
      isLoggedIn: false,
      username: '',
      pages: [
        {name: '功能介绍', index: '/Function'},
        {name: '学生管理', index: '/StudentManagement'},
        {name: '监控管理', index: '/CameraManagement'},
        {name: '学生轨迹追踪', index: '/TrackVisualization'}
      ]
    }
  },
  created () {
    // 检查登录状态
    this.checkLoginStatus()
  },
  methods: {
    goHome () {
      this.$router.push('/')
    },
    checkLoginStatus () {
      const token = localStorage.getItem('token')
      const user = JSON.parse(localStorage.getItem('user') || '{}')

      if (token && user.username) {
        this.isLoggedIn = true
        this.username = user.username
      } else {
        this.isLoggedIn = false
        this.username = ''
      }
    },
    handleCommand (command) {
      if (command === 'logout') {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        this.isLoggedIn = false
        this.$message.success('已退出登录')
        this.$router.push('/')
      } else if (command === 'profile') {
        this.$router.push('/profile')
      }
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
  position: relative;
  display: flex;
  align-items: center;
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

/* 简化菜单样式 */
.simple-menu {
  display: flex;
  align-items: center;
  padding: 0 3%;
  background-color: rgba(0, 0, 0, 0.525);
  height: 135px;
}

.menu-right {
  position: absolute;
  right: 3%;
  top: 50%;
  transform: translateY(-50%);
  margin-right: 20px;
}

.el-dropdown-link {
  color: #fff;
  cursor: pointer;
  font-size: 16px;
}
</style>
