<template>
  <div class="container">
    <Menu></Menu>
    <div class="content">
      <div class="management-layout">
        <!-- 左侧摄像头列表 -->
        <div class="content-left">
          <el-card shadow="always" class="camera-list-card">
            <div slot="header" class="clearfix">
              <span><b>监控列表</b></span>
              <el-button
                style="float: right; padding: 3px 0"
                type="text"
                @click="showAddCameraDialog">
                <i class="el-icon-plus"></i> 添加监控
              </el-button>
            </div>

            <el-input
              placeholder="搜索监控名称"
              v-model="searchQuery"
              clearable
              prefix-icon="el-icon-search"
              class="search-input">
            </el-input>

            <div class="table-container">
              <el-table
                :data="filteredCameras"
                style="width: 100%"
                highlight-current-row
                @current-change="handleCameraSelection">
                <el-table-column
                  prop="camera_id"
                  label="ID"
                  width="60">
                </el-table-column>
                <el-table-column
                  prop="name"
                  label="监控名称">
                </el-table-column>
                <el-table-column
                  label="操作"
                  width="150">
                  <template slot-scope="scope">
                    <el-button
                      size="mini"
                      type="primary"
                      icon="el-icon-edit"
                      circle
                      @click.stop="handleEdit(scope.row)">
                    </el-button>
                    <el-button
                      size="mini"
                      type="danger"
                      icon="el-icon-delete"
                      circle
                      @click.stop="handleDelete(scope.row)">
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </div>

        <!-- 右侧内容：地图与监控视频 -->
        <div class="content-right">
          <!-- 地图组件 -->
          <el-card shadow="always" class="map-card">
            <div slot="header" class="clearfix">
              <span><b>监控位置地图</b></span>
            </div>
            <div class="map-container">
              <CameraMapComponent
                :cameraList="cameras"
                :selectedCamera="selectedCamera"
                @select-camera="handleCameraSelection"
                @view-history="showHistoryVideo"
                @view-live="openLiveVideo">
              </CameraMapComponent>
            </div>
          </el-card>
        </div>
      </div>
    </div>

    <!-- 添加/编辑摄像头对话框 -->
    <el-dialog :title="dialogType === 'add' ? '添加监控' : '编辑监控'" :visible.sync="dialogVisible">
      <el-form :model="cameraForm" :rules="cameraRules" ref="cameraForm" label-width="100px">
        <el-form-item label="监控名称" prop="name">
          <el-input v-model="cameraForm.name" placeholder="请输入监控名称"></el-input>
        </el-form-item>
        <el-form-item label="X坐标" prop="location_x">
          <el-input v-model.number="cameraForm.location_x" placeholder="请输入X坐标"></el-input>
        </el-form-item>
        <el-form-item label="Y坐标" prop="location_y">
          <el-input v-model.number="cameraForm.location_y" placeholder="请输入Y坐标"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="submitCameraForm">确 定</el-button>
      </span>
    </el-dialog>

    <!-- 实时监控对话框 -->
    <el-dialog
      title="实时监控"
      :visible.sync="liveVideoDialogVisible"
      :before-close="closeLiveVideoDialog"
      width="70%">
      <div class="live-video-dialog">
        <div class="video-info">
          <h3>{{ selectedCamera ? `监控 #${selectedCamera.camera_id} - ${selectedCamera.name}` : '监控视频' }}</h3>
        </div>
        <div class="video-container">
          <video ref="liveVideo" autoplay class="camera-video"></video>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button
          :type="isMonitoring ? 'danger' : 'success'"
          @click="handleMonitoringToggle">
          {{ isMonitoring ? '停止监控' : '开始监控' }}
        </el-button>
        <el-button @click="closeLiveVideoDialog">关闭</el-button>
      </span>
    </el-dialog>

    <!-- 历史录像对话框 -->
    <el-dialog
      title="历史录像"
      :visible.sync="historyVideoDialogVisible"
      :before-close="closeHistoryVideoDialog"
      width="80%">
      <div class="history-video-dialog">
        <div class="video-info">
          <h3>{{ selectedCamera ? `监控 #${selectedCamera.camera_id} - ${selectedCamera.name}` : '监控视频' }}</h3>
        </div>
        <div class="history-video-content">
          <div class="video-container">
            <div v-if="videoUrl" class="video-player">
              <video controls autoplay class="camera-video">
                <source :src="videoUrl" type="video/mp4">
                您的浏览器不支持视频播放
              </video>
            </div>
            <div v-else class="no-video">
              <i class="el-icon-video-camera"></i>
              <p>请选择日期和时间段查看录像</p>
            </div>
          </div>

          <div class="video-controls">
            <el-form :inline="true" class="time-select-form">
              <el-form-item label="日期">
                <el-date-picker
                  v-model="selectedDate"
                  type="date"
                  placeholder="选择日期"
                  format="yyyy-MM-dd"
                  value-format="yyyy-MM-dd"
                  @change="dateChanged">
                </el-date-picker>
              </el-form-item>
              <el-form-item label="时间段" v-if="selectedDate">
                <el-select
                  v-model="selectedTimeRange"
                  placeholder="选择时间段"
                  @change="loadVideo">
                  <el-option
                    v-for="item in availableTimeRanges"
                    :key="item.id"
                    :label="`${item.start_time} - ${item.end_time}`"
                    :value="item.id">
                  </el-option>
                </el-select>
              </el-form-item>
            </el-form>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="closeHistoryVideoDialog">关闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'
import CameraMapComponent from '@/components/CameraMapComponent.vue'
import {
  getAllCameras,
  addCamera,
  updateCamera,
  deleteCamera,
  getCameraVideos
} from '../api/api'

export default {
  name: 'CameraManagement',
  components: {
    Menu,
    CameraMapComponent
  },
  data () {
    return {
      // 摄像头列表和搜索
      cameras: [],
      searchQuery: '',
      selectedCamera: null,

      // 对话框控制
      dialogVisible: false,
      dialogType: 'add', // 'add' 或 'edit'
      liveVideoDialogVisible: false,
      historyVideoDialogVisible: false,

      // 历史视频播放相关
      selectedDate: '',
      selectedTimeRange: null,
      availableTimeRanges: [],
      videoUrl: '',

      // 实时视频流
      liveStream: null,

      // 添加监控状态属性
      isMonitoring: true,

      // 添加/编辑摄像头对话框
      cameraForm: {
        camera_id: null,
        name: '',
        location_x: 0,
        location_y: 0
      },
      cameraRules: {
        name: [
          { required: true, message: '请输入监控名称', trigger: 'blur' },
          { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
        ],
        location_x: [
          { required: true, message: '请输入X坐标', trigger: 'blur' },
          { type: 'number', message: '坐标必须为数字值', trigger: 'blur' }
        ],
        location_y: [
          { required: true, message: '请输入Y坐标', trigger: 'blur' },
          { type: 'number', message: '坐标必须为数字值', trigger: 'blur' }
        ]
      }
    }
  },
  computed: {
    filteredCameras () {
      if (!this.searchQuery) {
        return this.cameras
      }
      const query = this.searchQuery.toLowerCase()
      return this.cameras.filter(camera =>
        camera.name.toLowerCase().includes(query) ||
        camera.camera_id.toString().includes(query)
      )
    }
  },
  created () {
    this.loadCameras()
    // 添加百度地图API
    this.loadBaiduMapApi()
  },
  beforeDestroy () {
    // 确保在组件销毁前停止所有视频流
    this.stopLiveVideo()
  },
  methods: {
    // 加载百度地图API
    loadBaiduMapApi () {
      // 检查是否已经加载过百度地图API
      if (window.BMapGL) {
        return Promise.resolve()
      }

      return new Promise((resolve, reject) => {
        // 在这里替换为你的百度地图API密钥
        const API_KEY = 'DEB9iPaH84MzxKOyR9oKAk99GYC7bgXr'

        // 创建script标签
        const script = document.createElement('script')
        script.type = 'text/javascript'
        script.src = `https://api.map.baidu.com/api?v=1.0&type=webgl&ak=${API_KEY}&callback=onBMapCallback`

        // 设置回调函数
        window.onBMapCallback = function () {
          console.log('百度地图API加载完成')
          resolve()
        }

        // 处理错误
        script.onerror = function () {
          reject(new Error('百度地图API加载失败'))
        }

        // 添加到文档
        document.head.appendChild(script)
      })
    },

    // 加载所有摄像头
    loadCameras () {
      getAllCameras().then(res => {
        if (res.data && res.data.status === 'success') {
          this.cameras = res.data.data
          // 如果之前有选中的摄像头，重新选择它
          if (this.selectedCamera) {
            const camera = this.cameras.find(c => c.camera_id === this.selectedCamera.camera_id)
            if (camera) {
              this.selectedCamera = camera
            }
          }
        } else {
          this.$message.error('加载摄像头列表失败')
        }
      }).catch(err => {
        console.error('加载摄像头失败', err)
        this.$message.error('加载摄像头列表失败')
      })
    },

    // 选择摄像头
    handleCameraSelection (camera) {
      if (camera) {
        this.selectedCamera = camera
      }
    },

    // 显示添加摄像头对话框
    showAddCameraDialog () {
      this.dialogType = 'add'
      this.cameraForm = {
        camera_id: null,
        name: '',
        location_x: 118.719706, // 默认位置：校园中心点
        location_y: 30.909573
      }
      this.dialogVisible = true
    },

    // 编辑摄像头
    handleEdit (camera) {
      this.dialogType = 'edit'
      this.cameraForm = { ...camera }
      this.dialogVisible = true
    },

    // 删除摄像头
    handleDelete (camera) {
      this.$confirm(`确定要删除监控 ${camera.camera_id}: ${camera.name} 吗?`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        deleteCamera(camera.camera_id).then(res => {
          if (res.data && res.data.status === 'success') {
            this.$message.success('删除成功')
            // 重新加载摄像头列表
            this.loadCameras()
            // 如果删除的是当前选中的摄像头，清除选择
            if (this.selectedCamera && this.selectedCamera.camera_id === camera.camera_id) {
              this.selectedCamera = null
              this.closeAllVideoDialogs()
            }
          } else {
            this.$message.error(res.data.message || '删除失败')
          }
        }).catch(err => {
          console.error('删除摄像头失败', err)
          this.$message.error('删除失败')
        })
      }).catch(() => {
        // 取消删除
      })
    },

    // 提交摄像头表单
    submitCameraForm () {
      this.$refs.cameraForm.validate(valid => {
        if (!valid) {
          return false
        }

        const formData = {
          name: this.cameraForm.name,
          location_x: this.cameraForm.location_x,
          location_y: this.cameraForm.location_y
        }

        if (this.dialogType === 'add') {
          // 添加新摄像头
          addCamera(formData).then(res => {
            if (res.data && res.data.status === 'success') {
              this.$message.success('添加成功')
              this.dialogVisible = false
              this.loadCameras()
            } else {
              this.$message.error(res.data.message || '添加失败')
            }
          }).catch(err => {
            console.error('添加摄像头失败', err)
            this.$message.error('添加失败')
          })
        } else {
          // 更新摄像头
          const updateData = {
            ...formData,
            camera_id: this.cameraForm.camera_id
          }
          updateCamera(updateData).then(res => {
            if (res.data && res.data.status === 'success') {
              this.$message.success('更新成功')
              this.dialogVisible = false
              this.loadCameras()
            } else {
              this.$message.error(res.data.message || '更新失败')
            }
          }).catch(err => {
            console.error('更新摄像头失败', err)
            this.$message.error('更新失败')
          })
        }
      })
    },

    // 显示历史视频
    showHistoryVideo (cameraId) {
      // 重置视频相关状态
      this.selectedDate = ''
      this.selectedTimeRange = null
      this.availableTimeRanges = []
      this.videoUrl = ''

      // 确保选中对应的摄像头
      if (!this.selectedCamera || this.selectedCamera.camera_id !== cameraId) {
        const camera = this.cameras.find(c => c.camera_id === cameraId)
        if (camera) {
          this.selectedCamera = camera
        }
      }

      // 打开历史视频对话框
      this.historyVideoDialogVisible = true
    },

    // 关闭历史视频对话框
    closeHistoryVideoDialog () {
      this.historyVideoDialogVisible = false
      this.videoUrl = ''
    },

    // 打开实时监控
    openLiveVideo (cameraId) {
    // 确保选中对应的摄像头
      if (!this.selectedCamera || this.selectedCamera.camera_id !== cameraId) {
        const camera = this.cameras.find(c => c.camera_id === cameraId)
        if (camera) {
          this.selectedCamera = camera
        }
      }

      // 打开实时视频对话框
      this.liveVideoDialogVisible = true
      this.isMonitoring = true // 默认开始监控

      // 停止当前可能存在的视频流
      this.stopLiveVideo()

      // 使用 WebRTC 打开用户的摄像头
      this.$nextTick(() => {
        this.startLiveVideo()
      })
    },

    // 处理监控按钮点击
    handleMonitoringToggle () {
      if (this.isMonitoring) {
        this.stopLiveVideo()
        this.isMonitoring = false
      } else {
        this.startLiveVideo()
        this.isMonitoring = true
      }
    },

    // 关闭实时视频对话框
    closeLiveVideoDialog () {
      this.stopLiveVideo()
      this.liveVideoDialogVisible = false
      this.isMonitoring = true // 重置状态
    },

    // 关闭所有视频对话框
    closeAllVideoDialogs () {
      this.stopLiveVideo()
      this.liveVideoDialogVisible = false
      this.historyVideoDialogVisible = false
      this.videoUrl = ''
    },

    // 启动实时视频
    startLiveVideo () {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        this.$message.error('您的浏览器不支持访问摄像头，请更换浏览器')
        return
      }

      navigator.mediaDevices.getUserMedia({ video: true, audio: false })
        .then(stream => {
          this.liveStream = stream
          const video = this.$refs.liveVideo
          if (video) {
            video.srcObject = stream
          }
        })
        .catch(err => {
          console.error('无法访问摄像头:', err)
          this.$message.error('无法访问摄像头，请确保摄像头已连接并授予访问权限')
        })
    },

    // 停止实时视频
    stopLiveVideo () {
      if (this.liveStream) {
        this.liveStream.getTracks().forEach(track => track.stop())
        this.liveStream = null
      }
    },

    // 日期变更时加载可用时间段
    dateChanged () {
      if (!this.selectedCamera || !this.selectedDate) {
        this.availableTimeRanges = []
        this.selectedTimeRange = null
        this.videoUrl = ''
        return
      }

      getCameraVideos(this.selectedCamera.camera_id, this.selectedDate).then(res => {
        if (res.data && res.data.status === 'success') {
          this.availableTimeRanges = res.data.data
          this.selectedTimeRange = null
          this.videoUrl = ''
        } else {
          this.$message.error(res.data.message || '加载可用时间段失败')
        }
      }).catch(err => {
        console.error('加载时间段失败', err)
        this.$message.error('加载可用时间段失败')
      })
    },

    // 加载历史视频
    // 修改 frontend/src/views/CameraManagement.vue 中的 loadVideo 方法

    loadVideo () {
      if (!this.selectedCamera || !this.selectedDate || !this.selectedTimeRange) {
        this.videoUrl = ''
        return
      }

      const timeRange = this.availableTimeRanges.find(t => t.id === this.selectedTimeRange)
      if (!timeRange) {
        this.videoUrl = ''
        return
      }

      this.videoUrl = timeRange.video_path
    }
  }
}
</script>

<style scoped>
.container {
  background: url("../assets/bg5.jpg") no-repeat center;
  background-size: 100% 100%;
}

.title {
  background-color: #409EFF;
  color: white;
  padding: 15px 20px;
  font-size: 18px;
  font-weight: bold;
}

.content {
  flex: 1;
  padding: 20px;
  overflow: auto;
}

.management-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 120px);
}

.content-left {
  width: 400px;
  display: flex;
  flex-direction: column;
}

.content-right {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.camera-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-input {
  margin-bottom: 15px;
}

.table-container {
  flex: 1;
  overflow: auto;
}

.map-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.map-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  min-height: 500px; /* 地图的最小高度 */
}

.clearfix::after {
  content: "";
  display: table;
  clear: both;
}

/* 对话框内容样式 */
.live-video-dialog,
.history-video-dialog {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.video-info {
  margin-bottom: 15px;
}

.video-info h3 {
  margin: 0;
  color: #303133;
}

.history-video-content {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.video-container {
  width: 100%;
  height: 550px;
  background-color: #f5f7fa;
  border-radius: 4px;
  overflow: hidden;
  display: flex;
  justify-content: center;
  align-items: center;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.video-controls {
  margin-top: 15px;
}

.no-video {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
}

.no-video i {
  font-size: 48px;
  margin-bottom: 10px;
}

.time-select-form {
  display: flex;
  justify-content: center;
}
</style>
