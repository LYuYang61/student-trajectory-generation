<template>
  <div class="container">
      <Menu></Menu>
    <div class="title">
      <p>基于深度学习的校园学生轨迹追踪系统设计与实现</p>
    </div>
    <!--
    <div class="button">
      <el-button type="info" round @click="startTracking">
        <span>点击进入</span>
      </el-button>
    </div>
    -->
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'

export default {
  name: 'Home',
  components: {
    Menu
  },
  data () {
    return {}
  },
  methods: {
    startTracking () {
      this.$router.push({path: '/Function'})
    }
  }
}
</script>

<style scoped>
.container {
  background: url("../assets/home_page.jpg") no-repeat center;
  background-size: 100% 100%;
}

.container::after {
  z-index: -1;
  position: absolute;
  content: '';
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgb(9, 9, 9);
  opacity: 0.3;
}

.logo {
  margin-left: 3%;
  padding-top: 3%;
  width: 8%;
}

.logo img {
  width: 100%;
  z-index: 2;
}

.title {
  margin-top: 7%;
  font-size: 4vw;
  color: #ffffff;
}

.title span {
  letter-spacing: 2vw;
}

.content {
  margin-top: 3%;
  color: #ffffff;
  font-size: 3vw;
}

.button {
  margin-top: 2%;
}

.button span {
  letter-spacing: 0.8vw;
}

.button button {
  width: 20%;
  font-size: 2vw;
  /* line-height: 10vh; */
  border: 1px solid white;
  border-radius: 8px;
  color: white;
  background: none;
  height: 70px;
  width: 230px;
}

.button button:hover {
  border: none;
  background-color: rgba(255, 255, 255, 0.763);
  color: #4d86ff;
}
</style>
