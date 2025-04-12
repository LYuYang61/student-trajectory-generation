<template>
  <div id="allmap"></div>
</template>

<script>
export default {
  name: 'BaiduMap',
  mounted () {
    this.initMap() // 页面加载时初始化地图
  },
  methods: {
    initMap () {
      // 确保 BMapGL 已加载
      if (typeof BMapGL === 'undefined') {
        console.error('Baidu Map API 未加载，请检查 API 密钥！')
        return
      }

      // 创建地图实例
      // eslint-disable-next-line no-undef
      const map = new BMapGL.Map('allmap')
      // eslint-disable-next-line no-undef
      const point = new BMapGL.Point(118.718406, 30.909773) // 设置中心点和坐标
      map.centerAndZoom(point, 18) // 初始化地图，设置缩放级别

      // 开启鼠标滚轮缩放
      map.enableScrollWheelZoom(true)

      // 设置 3D 视角
      map.setHeading(90) // 旋转角度
      map.setTilt(60) // 俯仰角度
    }
  }
}
</script>

<style scoped>
#allmap {
  width: 100%;
  height: 100vh; /* 填满整个屏幕 */
}
</style>
