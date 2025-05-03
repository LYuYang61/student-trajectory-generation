<template>
  <div class="camera-map-container">
    <!-- 地图容器 -->
    <div id="cameraMap" class="map"></div>

    <!-- 地图控件 -->
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

    <!-- 经纬度信息显示 -->
    <div v-if="coordinatesInfo" class="coordinates-info">
      {{ coordinatesInfo }}
      <el-button
        size="mini"
        type="text"
        icon="el-icon-copy-document"
        @click="copyCoordinates">
        复制
      </el-button>
    </div>

    <!-- 其他原有元素 -->
    <div class="map-legend">
      <div class="legend-item">
        <div class="legend-point camera"></div>
        <span>监控摄像头</span>
      </div>
    </div>

    <!-- 加载中遮罩 -->
    <div v-if="loading" class="map-loading">
      <i class="el-icon-loading"></i>
      <p>地图加载中...</p>
    </div>
  </div>
</template>

<script>
import cameraIcon from '@/assets/camera-icon.png'
/* eslint-disable no-undef */
export default {
  name: 'CameraMapComponent',
  props: {
    cameraList: {
      type: Array,
      default: () => []
    },
    selectedCamera: {
      type: Object,
      default: null
    }
  },
  data () {
    return {
      map: null,
      is3D: true,
      markers: [],
      infoWindows: [],
      loading: true,
      mapInitialized: false,
      buildings: [],
      coordinatesInfo: ''
    }
  },
  watch: {
    cameraList: {
      handler (newVal) {
        console.log('摄像头数据更新:', newVal)
        if (newVal && this.map && this.mapInitialized) {
          this.renderCameraMarkers()
        }
      },
      deep: true,
      immediate: false
    },
    selectedCamera: {
      handler (newVal) {
        if (newVal && this.map && this.mapInitialized) {
          this.centerMapOnCamera(newVal)
        }
      },
      deep: true,
      immediate: false
    }
  },
  mounted () {
    // 确保百度地图API已加载
    this.checkBaiduMapApiAndInit()
  },
  methods: {
    // 复制坐标到剪贴板
    copyCoordinates () {
      if (!this.coordinatesInfo) return

      const el = document.createElement('textarea')
      el.value = this.coordinatesInfo
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)

      this.$message({
        message: '坐标已复制到剪贴板',
        type: 'success',
        duration: 1500
      })
    },

    // 复制文本到剪贴板的通用方法
    copyTextToClipboard (text) {
      const el = document.createElement('textarea')
      el.value = text
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)

      this.$message({
        message: '坐标已复制到剪贴板',
        type: 'success',
        duration: 1500
      })
    },

    checkBaiduMapApiAndInit () {
      // 如果BMapGL已经存在，直接初始化地图
      if (typeof BMapGL !== 'undefined') {
        this.initMap()
        return
      }

      // 如果BMapGL不存在，等待父组件的百度地图API加载完成
      const checkInterval = setInterval(() => {
        if (typeof BMapGL !== 'undefined') {
          clearInterval(checkInterval)
          this.initMap()
        }
      }, 200)

      // 设置超时，如果5秒后还未加载完成，则显示错误
      setTimeout(() => {
        if (!this.mapInitialized) {
          clearInterval(checkInterval)
          console.error('百度地图API加载超时')
          this.loading = false
          this.$message.error('地图加载失败，请刷新页面重试')
        }
      }, 5000)
    },

    initMap () {
      try {
        // 创建地图实例
        this.map = new BMapGL.Map('cameraMap')

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

        // 添加地图点击事件
        this.map.addEventListener('click', (e) => {
          console.log('地图点击事件：', e)

          // 兼容两种坐标格式 (latlng 和 point)
          if (e.latlng) {
            this.showCoordinates(e.latlng.lng, e.latlng.lat)
          } else if (e.point) {
            this.showCoordinates(e.point.lng, e.point.lat)
          } else {
            console.warn('无法获取点击位置的坐标')
          }
        })

        this.mapInitialized = true
        this.loading = false

        // 如果初始化时已有摄像头数据，则渲染摄像头标记
        if (this.cameraList && this.cameraList.length > 0) {
          this.$nextTick(() => {
            this.renderCameraMarkers()
          })
        }

        console.log('地图初始化成功')
      } catch (error) {
        console.error('地图初始化失败', error)
        this.loading = false
        this.$message.error('地图初始化失败，请检查API配置')
      }
    },

    // 添加新方法用于显示坐标信息
    showCoordinates (longitude, latitude) {
      // 格式化经纬度，保留6位小数
      const formattedLng = longitude.toFixed(6)
      const formattedLat = latitude.toFixed(6)

      // 显示经纬度信息
      this.coordinatesInfo = `经度: ${formattedLng}, 纬度: ${formattedLat}`

      // 可以选择复制到剪贴板
      this.$message({
        message: `经纬度已更新: ${formattedLng}, ${formattedLat}`,
        type: 'success',
        duration: 2000
      })
    },

    enable3DView () {
      // 开启 3D 效果
      if (this.map) {
        this.map.setHeading(60) // 设置地图旋转角度
        this.map.setTilt(50) // 设置地图倾斜角度
      }
    },

    disable3DView () {
      // 关闭 3D 效果
      if (this.map) {
        this.map.setHeading(0)
        this.map.setTilt(0)
      }
    },

    toggle3DView (value) {
      if (value) {
        this.enable3DView()
      } else {
        this.disable3DView()
      }
    },

    zoomIn () {
      if (this.map) {
        const zoom = this.map.getZoom()
        this.map.setZoom(zoom + 1)
      }
    },

    zoomOut () {
      if (this.map) {
        const zoom = this.map.getZoom()
        this.map.setZoom(zoom - 1)
      }
    },

    resetView () {
      // 重置地图视角
      if (this.map) {
        const centerPoint = new BMapGL.Point(118.719706, 30.909573)
        this.map.centerAndZoom(centerPoint, 18)

        if (this.is3D) {
          this.enable3DView()
        } else {
          this.disable3DView()
        }
      }
    },

    addBuildingMarkers () {
      if (!this.map || this.buildings.length === 0) return

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
        const infoWindow = new BMapGL.InfoWindow(`
          <div class="info-window">
            <h4>${building.name}</h4>
            <p>${building.description || '暂无描述'}</p>
          </div>
        `, {
          width: 250,
          height: 100,
          title: building.name
        })

        // 添加点击事件
        marker.addEventListener('click', () => {
          this.map.openInfoWindow(infoWindow, point)
        })
      })
    },

    addCampusBoundary () {
      // 校园边界点坐标数组
      const campusBoundaryPoints = [
        new BMapGL.Point(118.716365, 30.912654),
        new BMapGL.Point(118.722073, 30.912546),
        new BMapGL.Point(118.723103, 30.907825),
        new BMapGL.Point(118.716537, 30.906874)
      ]

      // 创建多边形
      const polygon = new BMapGL.Polygon(campusBoundaryPoints, {
        strokeColor: '#0066FF',
        strokeWeight: 2,
        strokeOpacity: 0.8,
        fillColor: '#99CCFF',
        fillOpacity: 0.2
      })

      // 添加到地图
      this.map.addOverlay(polygon)
    },

    renderCameraMarkers () {
      // 清除之前的所有摄像头标记
      this.clearCameraMarkers()

      if (!this.cameraList || !this.map) return

      console.log('正在渲染摄像头标记，共计:', this.cameraList.length)

      // 遍历摄像头列表，创建标记
      this.cameraList.forEach(camera => {
        // 兼容不同的坐标属性名称
        const lon = camera.longitude || camera.location_x
        const lat = camera.latitude || camera.location_y

        if (!lon || !lat) {
          console.warn('摄像头缺少坐标信息:', camera)
          return
        }

        console.log(`渲染摄像头 ${camera.camera_id}: 位置(${lon}, ${lat})`)

        const point = new BMapGL.Point(lon, lat)

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
          title: camera.name
        })

        // 创建信息窗口内容
        const infoWindowContent = `
          <div class="camera-info-window">
            <h4>${camera.name || '未命名摄像头'}</h4>
            <p>ID: ${camera.camera_id}</p>
            <p>经度: ${lon.toFixed(6)}, 纬度: ${lat.toFixed(6)}</p>
            <div class="info-window-actions">
              <button id="view-live-${camera.camera_id}" class="view-btn">查看实时监控</button>
              <button id="view-history-${camera.camera_id}" class="view-btn">查看历史录像</button>
              <button id="copy-coords-${camera.camera_id}" class="view-btn coord-btn">复制坐标</button>
            </div>
          </div>
        `

        // 创建信息窗口
        const infoWindow = new BMapGL.InfoWindow(infoWindowContent, {
          width: 280,
          height: 140,
          title: camera.name || '摄像头信息'
        })

        // 将信息窗口保存到数组中
        this.infoWindows.push({ id: camera.camera_id, window: infoWindow })

        // 添加点击事件
        marker.addEventListener('click', () => {
          // 关闭其他所有信息窗口
          this.closeAllInfoWindows()

          // 打开当前信息窗口
          this.map.openInfoWindow(infoWindow, point)

          // 选中当前摄像头
          this.$emit('select-camera', camera)

          // 使用 setTimeout 确保 DOM 已经渲染
          setTimeout(() => {
            // 绑定按钮点击事件
            const liveBtn = document.getElementById(`view-live-${camera.camera_id}`)
            const historyBtn = document.getElementById(`view-history-${camera.camera_id}`)
            const copyBtn = document.getElementById(`copy-coords-${camera.camera_id}`)

            if (liveBtn) {
              liveBtn.addEventListener('click', () => {
                this.$emit('view-live', camera.camera_id)
              })
            }

            if (historyBtn) {
              historyBtn.addEventListener('click', () => {
                this.$emit('view-history', camera.camera_id)
              })
            }

            if (copyBtn) {
              copyBtn.addEventListener('click', () => {
                const coordText = `经度: ${lon.toFixed(6)}, 纬度: ${lat.toFixed(6)}`
                this.copyTextToClipboard(coordText)
              })
            }
          }, 100)
        })

        // 添加标记到地图
        this.map.addOverlay(marker)

        // 将标记保存到数组中
        this.markers.push({ id: camera.camera_id, marker: marker })
      })

      // 设置地图视野以包含所有摄像头
      if (this.markers.length > 0) {
        this.fitMapToMarkers()
      }

      console.log(`成功渲染 ${this.markers.length} 个摄像头标记`)
    },

    // 新增：自动调整地图视野以显示所有标记
    fitMapToMarkers () {
      if (!this.map || this.markers.length === 0) return

      const bounds = new BMapGL.Bounds()
      let hasValidPoints = false

      this.markers.forEach(item => {
        const position = item.marker.getPosition()
        if (position) {
          bounds.extend(position)
          hasValidPoints = true
        }
      })

      if (hasValidPoints) {
        this.map.setViewport(bounds, {
          margins: [50, 50, 50, 50]
        })
      }
    },

    clearCameraMarkers () {
      // 清除所有标记
      this.markers.forEach(item => {
        this.map.removeOverlay(item.marker)
      })

      // 清空数组
      this.markers = []
      this.infoWindows = []
    },

    closeAllInfoWindows () {
      this.map.closeInfoWindow()
    },

    getCameraStatusText (status) {
      // 根据状态码返回状态文本
      const statusMap = {
        0: '离线',
        1: '在线',
        2: '故障',
        3: '维护中'
      }
      return statusMap[status] || '未知状态'
    },

    centerMapOnCamera (camera) {
      if (!camera || !this.map) return

      // 兼容不同的坐标属性名称
      const lon = camera.longitude || camera.location_x
      const lat = camera.latitude || camera.location_y

      if (!lon || !lat) {
        console.warn('所选摄像头缺少坐标信息:', camera)
        return
      }

      // 设置地图中心点
      const point = new BMapGL.Point(lon, lat)
      this.map.setCenter(point)

      // 查找对应的标记
      const marker = this.markers.find(item => item.id === camera.camera_id)
      if (marker) {
        // 查找对应的信息窗口
        const infoWindowObj = this.infoWindows.find(item => item.id === camera.camera_id)
        if (infoWindowObj) {
          // 关闭其他所有信息窗口
          this.closeAllInfoWindows()

          // 打开当前信息窗口
          this.map.openInfoWindow(infoWindowObj.window, point)
        }
      }
    }
  },
  beforeDestroy () {
    // 组件销毁前清除标记和地图
    if (this.map) {
      this.clearCameraMarkers()
      this.map = null
    }
  }
}
</script>

<style scoped>
.camera-map-container {
  position: relative;
  width: 100%;
  height: 600px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

.map {
  width: 100%;
  height: 100%;
}

.map-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 8px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.map-legend {
  position: absolute;
  bottom: 20px;
  left: 20px;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.8);
  padding: 8px 12px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.legend-point {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

.legend-point.camera {
  background-color: #409EFF;
  border: 2px solid #fff;
}

.map-loading {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.7);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 20;
}

.coordinates-info {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 10;
  background-color: rgba(255, 255, 255, 0.9);
  padding: 8px 12px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  font-size: 14px;
  color: #606266;
  display: flex;
  align-items: center;
}

.coordinates-info .el-button {
  margin-left: 8px;
  padding: 3px;
}

/* 信息窗口样式 */
:deep(.camera-info-window) {
  padding: 8px;
}

:deep(.camera-info-window h4) {
  margin: 0 0 8px 0;
  color: #303133;
}

:deep(.camera-info-window p) {
  margin: 5px 0;
  color: #606266;
}

:deep(.info-window-actions) {
  margin-top: 10px;
  text-align: center;
}

:deep(.view-btn) {
  padding: 5px 12px;
  background-color: #409EFF;
  color: white;
  border: none;
  border-radius: 3px;
  cursor: pointer;
}

:deep(.view-btn:hover) {
  background-color: #66b1ff;
}

:deep(.coord-btn) {
  margin-top: 5px;
  background-color: #67c23a;
}

:deep(.coord-btn:hover) {
  background-color: #85ce61;
}
</style>
