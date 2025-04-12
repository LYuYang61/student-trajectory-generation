<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <span>轨迹可视化</span>
    </div>
    <div class="content">
      <div class="content-left">
        <BaiduMap class="baidu-map"></BaiduMap>
      </div>
      <div class="content-right">
        <el-card shadow="always" class="card">
          <div slot="header" class="clearfix">
            <span><b>轨迹信息</b></span>
          </div>
          <div class="track-info">
            <p>这里可以显示一些轨迹相关的信息</p>
          </div>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script>
import Menu from '@/components/Menu.vue'
import BaiduMap from '@/components/map.vue'

export default {
  name: 'TrackVisualization',
  components: {
    Menu,
    BaiduMap
  }
}
</script>

<style scoped>
@import "../static/css/mediaTracking.css";

.container {
  background: url("../assets/bg5.jpg") no-repeat center;
  background-size: 100% 100%;
  padding-top: 0px; /* Add some padding to the top to push the map up */
}

.title {
  font-size: 3vw;
  color: #5485c2;
  margin-bottom: 20px;
}

.content {
  display: flex; /* Use flexbox for layout */
  align-items: flex-start; /* Align content from the top */
  margin-bottom: 20px; /* Add some space below the map */
}

.content-left {
  flex: 3;
  display: flex;
  justify-content: center;
}

.content-right {
  flex: 1;
  padding: 5px;
}

.baidu-map {
  width: 100%;
}

.card {
  margin: 10px;
}

.track-info {
  padding: 10px;
  border: 1px solid #ccc;
  text-align: center;
}
</style>
