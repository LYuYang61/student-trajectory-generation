<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <span>监控管理</span>
    </div>
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

        <!-- 右侧监控视频和详情 -->
        <div class="content-right">
          <el-card shadow="always" class="video-card" v-if="selectedCamera">
            <div slot="header" class="clearfix">
              <span><b>监控 #{{ selectedCamera.camera_id }} - {{ selectedCamera.name }}</b></span>
              <div class="location-info">
                位置: ({{ selectedCamera.location_x.toFixed(6) }}, {{ selectedCamera.location_y.toFixed(6) }})
              </div>
            </div>

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
          </el-card>

          <el-card shadow="always" class="video-card" v-else>
            <div class="no-camera-selected">
              <i class="el-icon-video-camera-solid"></i>
              <p>请从左侧选择一个监控设备</p>
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
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'
import {
  getAllCameras,
  addCamera,
  updateCamera,
  deleteCamera,
  getCameraVideos
} from '../api/api'

export default {
  name: 'CameraManagement',
  components: { Menu },
  data () {
    return {
      // 摄像头列表和搜索
      cameras: [],
      searchQuery: '',
      selectedCamera: null,

      // 视频播放相关
      selectedDate: '',
      selectedTimeRange: null,
      availableTimeRanges: [],
      videoUrl: '',

      // 添加/编辑摄像头对话框
      dialogVisible: false,
      dialogType: 'add', // 'add' 或 'edit'
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
  },
  methods: {
    // 加载所有摄像头
    loadCameras () {
      getAllCameras().then(res => {
        this.cameras = res.data.data
        // 如果之前有选中的摄像头，重新选择它
        if (this.selectedCamera) {
          const camera = this.cameras.find(c => c.camera_id === this.selectedCamera.camera_id)
          if (camera) {
            this.selectedCamera = camera
          }
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
        this.selectedDate = ''
        this.selectedTimeRange = null
        this.availableTimeRanges = []
        this.videoUrl = ''
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
        this.availableTimeRanges = res.data.data
        this.selectedTimeRange = null
        this.videoUrl = ''
      }).catch(err => {
        console.error('加载时间段失败', err)
        this.$message.error('加载可用时间段失败')
      })
    },

    // 加载视频
    loadVideo () {
      if (!this.selectedCamera || !this.selectedDate || !this.selectedTimeRange) {
        this.videoUrl = ''
        return
      }

      const timeRange = this.availableTimeRanges.find(t => t.id === this.selectedTimeRange)
      if (timeRange) {
        // 直接使用返回的完整OSS URL
        this.videoUrl = timeRange.video_path
      }
    },

    // 显示添加摄像头对话框
    showAddCameraDialog () {
      this.dialogType = 'add'
      this.cameraForm = {
        camera_id: null,
        name: '',
        location_x: 0,
        location_y: 0
      }
      this.dialogVisible = true
    },

    // 显示编辑摄像头对话框
    handleEdit (camera) {
      this.dialogType = 'edit'
      this.cameraForm = {
        camera_id: camera.camera_id,
        name: camera.name,
        location_x: camera.location_x,
        location_y: camera.location_y
      }
      this.dialogVisible = true
    },

    // 删除摄像头
    handleDelete (camera) {
      this.$confirm(`确认删除监控 "${camera.name}"?`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        deleteCamera(camera.camera_id).then(() => {
          this.$message.success('删除成功')
          // 如果删除的是当前选中的摄像头，清空选择
          if (this.selectedCamera && this.selectedCamera.camera_id === camera.camera_id) {
            this.selectedCamera = null
            this.selectedDate = ''
            this.selectedTimeRange = null
            this.videoUrl = ''
          }
          this.loadCameras()
        }).catch(err => {
          console.error('删除失败', err)
          this.$message.error('删除监控失败')
        })
      }).catch(() => {
        // 取消删除，不做操作
      })
    },

    // 提交摄像头表单
    submitCameraForm () {
      this.$refs.cameraForm.validate(valid => {
        if (!valid) {
          return false
        }

        if (this.dialogType === 'add') {
          // 添加摄像头
          addCamera(this.cameraForm).then(() => {
            this.$message.success('添加成功')
            this.dialogVisible = false
            this.loadCameras()
          }).catch(err => {
            console.error('添加失败', err)
            this.$message.error('添加监控失败')
          })
        } else {
          // 编辑摄像头
          updateCamera(this.cameraForm).then(() => {
            this.$message.success('更新成功')
            this.dialogVisible = false
            this.loadCameras()
          }).catch(err => {
            console.error('更新失败', err)
            this.$message.error('更新监控失败')
          })
        }
      })
    }
  }
}
</script>

<style scoped>
@import "../static/css/mediaTracking.css";

.container {
  background: url("../assets/bg5.jpg") no-repeat center;
  background-size: 100% 100%;
}

.title {
  font-size: 3vw;
  color: #5485c2;
}

.management-layout {
  display: flex;
  gap: 20px;
}

.content-left {
  flex: 1;
  max-width: 450px;
}

.content-right {
  flex: 2;
}

.camera-list-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.search-input {
  margin-bottom: 15px;
}

/* 新增加的表格容器样式，用于实现滚动条 */
.table-container {
  height: 250px;
  overflow-y: auto;
}

.video-card {
  height: 100%;
}

.video-container {
  height: 400px;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #f0f0f0;
  border-radius: 4px;
  margin-bottom: 20px;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.no-video, .no-camera-selected {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  color: #909399;
}

.no-video i, .no-camera-selected i {
  font-size: 48px;
  margin-bottom: 15px;
}

.time-select-form {
  display: flex;
  justify-content: center;
}

.location-info {
  font-size: 12px;
  color: #909399;
  margin-top: 5px;
}

/* 设置滚动条样式 */
.table-container::-webkit-scrollbar {
  width: 6px;
}

.table-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.table-container::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}

.table-container::-webkit-scrollbar-thumb:hover {
  background: #909399;
}

</style>
