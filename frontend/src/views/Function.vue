<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <span>请选择功能</span>
    </div>
    <div class="content">
      <el-button class="button2" type="info" circle @click="StudentManagement">
        <div class="btn-icon">
          <i class="el-icon-school"></i>
        </div>
        <div class="btn-title">
          <span>学生管理</span>
        </div>
        <div class="btn-content">
          <p>对学生的基本信息进行管理</p>
          <p>支持excel批量导入</p>
        </div>
      </el-button>
      <el-button class="button3" type="info" circle @click="CameraManagement">
        <div class="btn-icon">
          <i class="el-icon-video-camera"></i>
        </div>
        <div class="btn-title">
          <span>监控管理</span>
        </div>
        <div class="btn-content">
          <p>对校园监控基本信息进行管理</p>
          <p>支持历史视频观看和多目标跟踪</p>
          <p>支持查看实时监控</p>
        </div>
      </el-button>
      <el-button class="button4" type="info" circle @click="TrackVisualization">
        <div class="btn-icon">
          <i class="el-icon-view"></i>
        </div>
        <div class="btn-title">
          <span>学生轨迹追踪</span>
        </div>
        <div class="btn-content">
          <p>还原指定学生在特定时间段的大致轨迹</p>
          <p>支持学生关联属性、时间段选择</p>
        </div>
      </el-button>
    </div>
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'
export default {
  name: 'Function',
  components: {
    Menu
  },
  data () {
    return {}
  },
  methods: {
    // 监控管理
    CameraManagement () {
      this.$router.push({path: '/CameraManagement'})
    },
    // 学生管理
    StudentManagement () {
      this.$router.push({path: '/StudentManagement'})
    },
    // 学生轨迹追踪
    TrackVisualization () {
      this.$router.push({path: '/TrackVisualization'})
    }
  }
}
</script>

<style scoped>
.container {
  background: url("../assets/bg5.jpg") no-repeat center;
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
  background-color: rgba(0, 0, 0, 0.51);
  opacity: 0.3;
}

.logo {
  margin-left: 3%;
  padding-top: 3%;
  width: 8%;
}

.logo img {
  width: 100%;
}

.title {
  margin-top: 1%;
  font-size: 3vw;
  color: #5485c2;
  margin-left: 50px;
}

.title span {
  letter-spacing: 1vw;
}

.content {
  margin-top: 1%;
}

.content button {
  position: relative;
  width: 16%;
  height: 60vh;
  border-radius: 40px;
  transition: all 0.4s;
  margin: 1% 1%;
  /* text-align: center; */
}

.button2{
  background: url("../assets/but1.jpg");
  background-size: 288px 592px;
}

.button3{
  background: url("../assets/but2.jpg");
  background-size: 288px 592px;
}

.button4{
  background: url("../assets/but3.jpg");
  background-size: 288px 592px;
}

.content button:hover {
  width: 18%;
  height: 65vh;
  margin: 0 1%;
  transition: all 0.4s;
}

.content .btn-icon {
  width: 100%;
  position: absolute;
  top: 15%;
  left: 0;
  height: 10%;
  font-size: 4.5vh;
}
.content .btn-title {
  width: 100%;
  position: absolute;
  top: 40%;
  left: 0;
  height: 15%;
  font-size: 3.5vh;
}

.content .btn-title span {
  letter-spacing: .5vw;
}

.content .btn-content {
  width: 100%;
  position: absolute;
  top: 55%;
  left: 0;
  font-size: 2vh;
}

.content .btn-content p{
  margin-top: 5%;
}
</style>
