<template>
  <div class="map-container">
    <!-- Map container -->
    <div id="allmap" class="map"></div>

    <!-- Map controls -->
    <div class="map-controls">
      <el-button-group>
        <el-button size="small" icon="el-icon-zoom-in" @click="zoomIn"></el-button>
        <el-button size="small" icon="el-icon-zoom-out" @click="zoomOut"></el-button>
      </el-button-group>
      <el-button size="small" icon="el-icon-refresh-right" @click="resetView"></el-button>

      <el-divider direction="vertical"></el-divider>

      <el-switch
        v-model="is3D"
        active-text="3D视图"
        inactive-text="2D视图"
        @change="toggle3DView">
      </el-switch>
    </div>

    <!-- Legend for the map -->
    <div class="map-legend">
      <div class="legend-item">
        <div class="legend-line confirmed"></div>
        <span>确定轨迹</span>
      </div>
      <div class="legend-item">
        <div class="legend-line estimated"></div>
        <span>推测轨迹</span>
      </div>
      <div class="legend-item">
        <div class="legend-point camera"></div>
        <span>摄像头</span>
      </div>
    </div>
  </div>
</template>

<script>
import cameraIcon from '@/assets/camera-icon.png'
/* eslint-disable no-undef */
export default {
  name: 'BaiduMap',
  props: {
    trajectoryData: {
      type: Object,
      default: () => ({
        points: [],
        cameras: []
      })
    }
  },
  data () {
    return {
      map: null,
      is3D: true,
      markers: [],
      polylines: [],
      infoWindows: [],
      // 校园建筑物基本信息
      buildings: []
    }
  },
  watch: {
    trajectoryData: {
      handler (newVal) {
        console.log('轨迹数据更新:', newVal)
        if (newVal && this.map) {
          this.renderTrajectory()
        }
      },
      deep: true,
      immediate: false
    }
  },
  mounted () {
    this.initMap() // 初始化地图
  },
  updated () {
    // 确保在组件更新后，如果有轨迹数据且地图已初始化，则渲染轨迹
    if (this.trajectoryData && this.trajectoryData.points && this.trajectoryData.points.length > 0 && this.map) {
      this.renderTrajectory()
    }
  },
  methods: {
    initMap () {
      // 确保 BMapGL 已加载
      if (typeof BMapGL === 'undefined') {
        console.error('Baidu Map API 未加载，请检查 API 密钥！')
        return
      }

      // 创建地图实例
      this.map = new BMapGL.Map('allmap')

      // 设置中心点和缩放级别
      const centerPoint = new BMapGL.Point(118.719706, 30.909573) // 校园中心点
      this.map.centerAndZoom(centerPoint, 18)

      // 开启鼠标滚轮缩放和键盘控制
      this.map.enableScrollWheelZoom(true)
      this.map.enableKeyboard()

      // 添加地图控件
      this.map.addControl(new BMapGL.ScaleControl()) // 比例尺控件
      this.map.addControl(new BMapGL.ZoomControl()) // 缩放控件
      this.map.addControl(new BMapGL.LocationControl()) // 定位控件

      // 设置 3D 视角
      if (this.is3D) {
        this.enable3DView()
      }

      // 添加校园建筑物标记
      this.addBuildingMarkers()

      // 添加校园边界
      this.addCampusBoundary()

      // 如果初始化时已有轨迹数据，则渲染轨迹
      if (this.trajectoryData && this.trajectoryData.points && this.trajectoryData.points.length > 0) {
        this.$nextTick(() => {
          this.renderTrajectory()
        })
      }
    },

    enable3DView () {
      // 开启 3D 效果
      this.map.setHeading(60) // 设置地图旋转角度
      this.map.setTilt(50) // 设置地图倾斜角度
    },

    disable3DView () {
      // 关闭 3D 效果
      this.map.setHeading(0)
      this.map.setTilt(0)
    },

    toggle3DView (value) {
      if (value) {
        this.enable3DView()
      } else {
        this.disable3DView()
      }
    },

    zoomIn () {
      const zoom = this.map.getZoom()
      this.map.setZoom(zoom + 1)
    },

    zoomOut () {
      const zoom = this.map.getZoom()
      this.map.setZoom(zoom - 1)
    },

    resetView () {
      // 重置地图视角
      const centerPoint = new BMapGL.Point(118.719706, 30.909573)
      this.map.centerAndZoom(centerPoint, 18)

      if (this.is3D) {
        this.enable3DView()
      } else {
        this.disable3DView()
      }
    },

    addBuildingMarkers () {
      // 添加校园建筑物标记
      this.buildings.forEach(building => {
        const point = new BMapGL.Point(building.position[0], building.position[1])

        // 创建标记
        const marker = new BMapGL.Marker(point, {
          title: building.name
        })

        // 添加标记到地图
        this.map.addOverlay(marker)

        // 创建信息窗口
        const infoWindow = new BMapGL.InfoWindow(`<div class="info-window">
          <h4>${building.name}</h4>
          <p>校园建筑</p>
        </div>`, {
          width: 200,
          height: 100,
          title: building.name
        })

        // 点击标记时显示信息窗口
        marker.addEventListener('click', () => {
          this.map.openInfoWindow(infoWindow, point)
        })
      })
    },

    addCampusBoundary () {
      // 添加校园边界线
      const boundary = [
        new BMapGL.Point(118.714636, 30.91173),
        new BMapGL.Point(118.71866, 30.914929),
        new BMapGL.Point(118.7259, 30.912474),
        new BMapGL.Point(118.719321, 30.907731)
      ]

      // 创建多边形
      const polygon = new BMapGL.Polygon(boundary, {
        strokeColor: '#5485c2',
        strokeWeight: 2,
        strokeOpacity: 0.5,
        fillColor: '#5485c2',
        fillOpacity: 0.1
      })

      // 添加到地图
      this.map.addOverlay(polygon)
    },

    renderTrajectory () {
      // 确保地图已初始化
      if (!this.map) {
        console.error('地图未初始化，无法渲染轨迹')
        return
      }

      // 清除之前的轨迹
      this.clearTrajectory()

      console.log('渲染轨迹，数据：', this.trajectoryData)

      if (!this.trajectoryData || !this.trajectoryData.points || this.trajectoryData.points.length < 1) {
        console.warn('轨迹数据不完整或为空')
        return
      }

      // 生成轨迹线
      this.drawTrajectoryLines()

      // 添加摄像头标记
      if (this.trajectoryData.cameras && this.trajectoryData.cameras.length > 0) {
        this.addCameraMarkers()
      }

      // 调整地图视角以包含整个轨迹
      this.fitMapToTrajectory()
    },

    drawTrajectoryLines () {
      const points = this.trajectoryData.points

      // 检查点数据是否足够
      if (points.length < 2) {
        console.warn('轨迹点数量不足，至少需要2个点才能绘制线段')
        return
      }

      console.log(`开始绘制轨迹线，共${points.length}个点`)

      // 将所有点连接为一条线
      for (let i = 1; i < points.length; i++) {
        const prevPoint = points[i - 1]
        const currPoint = points[i]

        // 确保点有位置数据
        if (!prevPoint.position || !currPoint.position) {
          console.warn(`点 ${i - 1} 或 ${i} 缺少位置数据`, prevPoint, currPoint)
          continue
        }

        // 判断线段类型
        let strokeColor, strokeStyle

        // 根据点类型决定线的样式
        if ((prevPoint.type === 'camera' && currPoint.type === 'path') ||
          (prevPoint.type === 'path' && currPoint.type === 'camera') ||
          (prevPoint.type === 'camera' && currPoint.type === 'camera')) {
          // 确定轨迹 - 包含摄像头的路径
          strokeColor = '#67C23A'
          strokeStyle = 'solid'
        } else {
          // 推测轨迹 - 无摄像头确认的路径
          strokeColor = '#E6A23C'
          strokeStyle = 'dashed'
        }

        // 创建线段
        const polyline = new BMapGL.Polyline([
          new BMapGL.Point(prevPoint.position[0], prevPoint.position[1]),
          new BMapGL.Point(currPoint.position[0], currPoint.position[1])
        ], {
          strokeColor: strokeColor,
          strokeWeight: 5,
          strokeOpacity: 0.8,
          strokeStyle: strokeStyle
        })

        // 添加到地图
        this.map.addOverlay(polyline)
        this.polylines.push(polyline)

        console.log(`已绘制线段 ${i}:`, prevPoint.position, '=>', currPoint.position)
      }
    },

    addCameraMarkers () {
      if (!this.trajectoryData.cameras || this.trajectoryData.cameras.length === 0) {
        console.warn('没有摄像头数据可添加')
        return
      }

      console.log(`添加摄像头标记，共${this.trajectoryData.cameras.length}个摄像头`)

      // 按照相机ID在轨迹中的顺序创建相机索引映射
      const cameraOrder = {}
      this.trajectoryData.cameras.forEach((camera, index) => {
        cameraOrder[camera.id] = index
      })

      this.trajectoryData.cameras.forEach((camera) => {
        if (!camera.position || camera.position.length !== 2) {
          console.warn(`摄像头 ${camera.id} 位置数据无效:`, camera)
          return
        }

        const point = new BMapGL.Point(camera.position[0], camera.position[1])

        // 创建自定义图标
        const myIcon = new BMapGL.Icon(
          cameraIcon, // 使用导入的图标变量
          new BMapGL.Size(24, 24),
          {
            anchor: new BMapGL.Size(12, 12),
            imageSize: new BMapGL.Size(24, 24)
          }
        )

        // 创建标记
        const marker = new BMapGL.Marker(point, {
          icon: myIcon,
          title: `摄像头 ${camera.id}: ${camera.name || '未命名'}`
        })

        // 添加到地图
        this.map.addOverlay(marker)
        this.markers.push(marker)

        // 创建信息窗口
        const infoWindow = new BMapGL.InfoWindow(`<div class="info-window">
          <h4>摄像头 ${camera.id}: ${camera.name || '未命名'}</h4>
          <p>时间: ${camera.timestamp || '未知'}</p>
          <button id="view-camera-${camera.id}" class="info-window-button">查看监控视频</button>
        </div>`, {
          width: 250,
          height: 120,
          title: `摄像头 ${camera.id}`
        })

        // 存储信息窗口
        this.infoWindows.push(infoWindow)

        // 添加点击事件
        marker.addEventListener('click', () => {
          this.map.openInfoWindow(infoWindow, point)

          // 使用 setTimeout 确保 DOM 已经渲染
          setTimeout(() => {
            const button = document.getElementById(`view-camera-${camera.id}`)
            if (button) {
              button.addEventListener('click', () => {
                this.$emit('camera-click', camera.id)
              })
            }
          }, 100)
        })

        // 添加标签 - 使用摄像头ID而不是索引
        const label = new BMapGL.Label(`${camera.id}`, {
          offset: new BMapGL.Size(5, 5)
        })
        label.setStyle({
          border: '1px solid #409EFF',
          backgroundColor: '#409EFF',
          color: 'white',
          borderRadius: '50%',
          fontSize: '12px',
          width: '20px',
          height: '20px',
          lineHeight: '20px',
          textAlign: 'center'
        })
        marker.setLabel(label)

        console.log(`已添加摄像头标记 ${camera.id}:`, camera.position)
      })
    },

    fitMapToTrajectory () {
      if (!this.trajectoryData.points || this.trajectoryData.points.length === 0) {
        console.warn('没有轨迹点，无法调整地图视角')
        return
      }

      // 获取所有点的范围
      const bounds = new BMapGL.Bounds()
      let hasValidPoints = false

      this.trajectoryData.points.forEach(point => {
        if (point.position && point.position.length === 2) {
          bounds.extend(new BMapGL.Point(point.position[0], point.position[1]))
          hasValidPoints = true
        }
      })

      if (!hasValidPoints) {
        console.warn('没有有效的轨迹点坐标')
        return
      }

      // 设置地图视图以包含所有点，并留一些边距
      this.map.setViewport(bounds, {
        margins: [50, 50, 50, 50]
      })

      console.log('已调整地图视角以适应轨迹')
    },

    clearTrajectory () {
      console.log('清除之前的轨迹标记和线条')

      // 清除之前的轨迹标记
      this.markers.forEach(marker => {
        this.map.removeOverlay(marker)
      })
      this.markers = []

      // 清除之前的轨迹线
      this.polylines.forEach(polyline => {
        this.map.removeOverlay(polyline)
      })
      this.polylines = []

      // 清除信息窗口
      this.infoWindows = []
    }
  }
}
</script>

<style scoped>
.map-container {
  position: relative;
  width: 100%;
  height: 100%;
}

.map {
  width: 100%;
  height: 100%;
  border-radius: 4px;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  background-color: white;
  padding: 5px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
}

.map-legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 1000;
  background-color: white;
  padding: 10px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.legend-line {
  width: 20px;
  height: 3px;
  margin-right: 8px;
}

.legend-line.confirmed {
  background-color: #67C23A;
}

.legend-line.estimated {
  background-color: #E6A23C;
  border-top: 1px dashed #E6A23C;
}

.legend-point {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
}

.legend-point.camera {
  background-color: #409EFF;
}

/* InfoWindow button style */
:deep(.info-window-button) {
  background-color: #409EFF;
  color: white;
  border: none;
  padding: 5px 10px;
  border-radius: 3px;
  cursor: pointer;
  margin-top: 5px;
}

:deep(.info-window-button:hover) {
  background-color: #337ecc;
}

:deep(.BMap_bubble_title) {
  font-weight: bold;
  background-color: #f5f7fa;
  padding: 8px;
  border-bottom: 1px solid #ebeef5;
}

:deep(.BMap_bubble_content) {
  padding: 10px;
}

:deep(.info-window h4) {
  margin: 0 0 5px 0;
  color: #303133;
}

:deep(.info-window p) {
  margin: 0 0 5px 0;
  color: #606266;
}
</style>
