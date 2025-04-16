<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <span>轨迹可视化</span>
    </div>

    <el-steps :active="activeStep" finish-status="success" class="steps-container">
      <el-step title="身份和属性过滤"></el-step>
      <el-step title="重识别处理"></el-step>
      <el-step title="轨迹可视化"></el-step>
    </el-steps>

    <!-- Step 1: Identity and Attribute Filtering -->
    <div v-if="activeStep === 1" class="content">
      <div class="content-left">
        <el-card shadow="always" class="input-card">
          <div slot="header" class="clearfix">
            <span><b>学生信息与属性过滤</b></span>
          </div>
          <el-form :model="filterForm" label-width="100px">
            <el-form-item label="学号">
              <el-input v-model="filterForm.studentId" placeholder="请输入学生学号"></el-input>
            </el-form-item>
            <el-form-item label="时间范围">
              <el-date-picker
                v-model="filterForm.timeRange"
                type="datetimerange"
                range-separator="至"
                start-placeholder="开始时间"
                end-placeholder="结束时间"
                format="yyyy-MM-dd HH:mm:ss"
                value-format="yyyy-MM-dd HH:mm:ss">
              </el-date-picker>
            </el-form-item>
            <el-form-item label="属性过滤">
              <el-checkbox-group v-model="filterForm.attributes">
                <el-checkbox label="umbrella">雨伞</el-checkbox>
                <el-checkbox label="backpack">背包</el-checkbox>
                <el-checkbox label="hat">帽子</el-checkbox>
                <el-checkbox label="glasses">眼镜</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="参考图片">
              <el-upload
                class="upload-demo"
                action="#"
                :http-request="handleImageUpload"
                :show-file-list="false"
                :before-upload="beforeImageUpload">
                <img v-if="filterForm.referenceImage" :src="filterForm.referenceImage" class="reference-image">
                <el-button v-else type="primary">点击上传参考图片</el-button>
                <div slot="tip" class="el-upload__tip">请上传清晰的正面照片，用于辅助识别</div>
              </el-upload>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="startFiltering">开始过滤</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
      <div class="content-right">
        <el-card shadow="always" class="card">
          <div slot="header" class="clearfix">
            <span><b>过滤结果预览</b></span>
          </div>
          <div class="filter-results" v-if="filterResults.length > 0">
            <div class="result-count">找到 {{ filterResults.length }} 条匹配记录</div>
            <el-carousel :interval="4000" type="card" height="200px">
              <el-carousel-item v-for="(item, index) in filterResults" :key="index">
                <div class="result-item">
                  <img :src="item.image" class="result-image">
                  <div class="result-info">
                    <p>摄像头: {{ item.cameraId }}</p>
                    <p>时间: {{ item.timestamp }}</p>
                    <p>匹配属性: {{ item.matchedAttributes.join(', ') }}</p>
                  </div>
                </div>
              </el-carousel-item>
            </el-carousel>
          </div>
          <div v-else class="no-results">
            <i class="el-icon-search"></i>
            <p>暂无匹配结果，请先进行过滤</p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Step 2: Re-identification Processing -->
    <div v-if="activeStep === 2" class="content">
      <div class="content-left">
        <el-card shadow="always" class="reid-card">
          <div slot="header" class="clearfix">
            <span><b>重识别处理</b></span>
          </div>
          <div class="reid-progress">
            <div class="progress-item">
              <span class="progress-label">时空约束过滤</span>
              <el-progress :percentage="reIdProgress.spatialTemporal" :status="reIdProgress.spatialTemporal === 100 ? 'success' : ''"></el-progress>
            </div>
            <div class="progress-item">
              <span class="progress-label">跨摄像头匹配</span>
              <el-progress :percentage="reIdProgress.crossCamera" :status="reIdProgress.crossCamera === 100 ? 'success' : ''"></el-progress>
            </div>
            <div class="progress-item">
              <span class="progress-label">特征提取与匹配</span>
              <el-progress :percentage="reIdProgress.featureMatching" :status="reIdProgress.featureMatching === 100 ? 'success' : ''"></el-progress>
            </div>
            <div class="progress-item">
              <span class="progress-label">轨迹整合</span>
              <el-progress :percentage="reIdProgress.trajectoryIntegration" :status="reIdProgress.trajectoryIntegration === 100 ? 'success' : ''"></el-progress>
            </div>
          </div>
          <div class="reid-options">
            <el-form :model="reIdOptions" label-width="120px">
              <el-form-item label="重识别算法">
                <el-select v-model="reIdOptions.algorithm">
                  <el-option label="OSNetReID" value="osnet"></el-option>
                  <el-option label="MGNReID" value="mgn"></el-option>
                  <el-option label="TransReID" value="transformer"></el-option>
                </el-select>
              </el-form-item>
              <el-form-item label="匹配阈值">
                <el-slider v-model="reIdOptions.threshold" :min="0" :max="100" :step="1"></el-slider>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" @click="startReId" :disabled="!canStartReId">开始重识别</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-card>
      </div>
      <div class="content-right">
        <el-card shadow="always" class="card">
          <div slot="header" class="clearfix">
            <span><b>重识别结果预览</b></span>
          </div>
          <div class="reid-results" v-if="reIdResults.length > 0">
            <div class="timeline">
              <el-timeline>
                <el-timeline-item
                  v-for="(item, index) in reIdResults"
                  :key="index"
                  :timestamp="item.timestamp"
                  :color="getTimelineColor(index)">
                  摄像头 {{ item.cameraId }} - {{ item.location }}
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>
          <div v-else class="no-results">
            <i class="el-icon-data-analysis"></i>
            <p>暂无重识别结果，请先完成处理</p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- Step 3: Trajectory Visualization -->
    <div v-if="activeStep === 3" class="content">
      <div class="content-left">
        <BaiduMap
          class="baidu-map"
          ref="baiduMap"
          :trajectory-data="trajectoryData"
          @camera-click="handleCameraClick">
        </BaiduMap>
      </div>
      <div class="content-right">
        <el-card v-if="!showVideo" shadow="always" class="card">
          <div slot="header" class="clearfix">
            <span><b>轨迹信息</b></span>
          </div>
          <div class="track-info">
            <div class="student-info">
              <p><b>学号:</b> {{ filterForm.studentId }}</p>
              <p><b>时间区间:</b> {{ formatTimeRange(filterForm.timeRange) }}</p>
              <p><b>经过摄像头:</b> {{ traversedCameras.join(' → ') }}</p>
              <p><b>轨迹长度:</b> {{ calculateTrajectoryLength() }} 米</p>
              <p><b>总用时:</b> {{ calculateTotalTime() }}</p>
            </div>
            <div class="trajectory-legend">
              <div class="legend-item">
                <div class="legend-color" style="background-color: #67C23A;"></div>
                <span>确定轨迹</span>
              </div>
              <div class="legend-item">
                <div class="legend-color" style="background-color: #E6A23C;"></div>
                <span>推测轨迹</span>
              </div>
              <div class="legend-item">
                <div class="legend-color" style="background-color: #409EFF;"></div>
                <span>摄像头位置</span>
              </div>
            </div>
          </div>
        </el-card>
        <el-card v-else shadow="always" class="card">
          <div slot="header" class="clearfix">
            <span><b>监控视频</b></span>
            <el-button style="float: right; padding: 3px 0" type="text" @click="closeVideo">关闭</el-button>
          </div>
          <div class="video-player">
            <div class="video-container">
              <video ref="videoPlayer" controls class="video-element" @canplay="handleCanPlay">
                <source :src="videoUrl" type="video/mp4">
                您的浏览器不支持 video 标签。
              </video>
            </div>
            <div class="video-info">
              <p><b>摄像头:</b> {{ selectedVideo.cameraId }}</p>
              <p><b>位置:</b> {{ selectedVideo.location }}</p>
              <p><b>时间:</b> {{ selectedVideo.timestamp }}</p>
            </div>
          </div>
        </el-card>
      </div>
    </div>

    <el-button-group class="nav-buttons">
      <el-button icon="el-icon-arrow-left" @click="prevStep" :disabled="activeStep === 1">上一步</el-button>
      <el-button type="primary" @click="nextStep" :disabled="!canGoToNextStep">
        {{ activeStep === 3 ? '完成' : '下一步' }}
        <i class="el-icon-arrow-right el-icon--right"></i>
      </el-button>
    </el-button-group>
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
  },
  data () {
    return {
      activeStep: 1,
      filterForm: {
        studentId: '',
        timeRange: [new Date(new Date().setHours(0, 0, 0, 0)), new Date()],
        attributes: [],
        referenceImage: ''
      },
      filterResults: [],
      reIdOptions: {
        algorithm: 'osnet',
        threshold: 70
      },
      reIdProgress: {
        spatialTemporal: 0,
        crossCamera: 0,
        featureMatching: 0,
        trajectoryIntegration: 0
      },
      reIdResults: [],
      trajectoryData: {
        points: [],
        cameras: []
      },
      showVideo: false,
      selectedVideo: {
        url: '',
        cameraId: '',
        location: '',
        timestamp: ''
      },
      // 模拟摄像头数据
      cameras: [
        { id: '1', name: '新安学堂', location: '新安学堂正门', position: [118.718797, 30.911546] },
        { id: '2', name: '图书馆', location: '图书馆正门', position: [118.716685, 30.909624] },
        { id: '3', name: '食堂', location: '南漪湖餐厅', position: [118.720928, 30.911897] },
        { id: '4', name: '操场', location: '操场正门', position: [118.722249, 30.912036] },
        { id: '5', name: '体育馆', location: '体育馆正门', position: [118.72153, 30.911107] }
      ],
      // 存储视频URL的基础路径
      baseVideoUrl: ''
    }
  },
  computed: {
    canStartReId () {
      return this.filterResults.length > 0
    },
    canGoToNextStep () {
      if (this.activeStep === 1) {
        return this.filterResults.length > 0
      } else if (this.activeStep === 2) {
        return this.reIdResults.length > 0
      }
      return true
    },
    traversedCameras () {
      return this.reIdResults.map(item => item.cameraId)
    },
    videoUrl () {
      // 使用基础URL和公共路径构建完整的视频URL
      return this.selectedVideo.url || ''
    }
  },
  created () {
    // 获取基础URL，用于正确构建资源路径
    this.baseVideoUrl = process.env.BASE_URL || ''
  },
  methods: {
    formatTimeRange (range) {
      if (!range || range.length !== 2) return ''
      const startDate = new Date(range[0])
      const endDate = new Date(range[1])
      const formatDate = (date) => {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
      }
      return `${formatDate(startDate)} 至 ${formatDate(endDate)}`
    },
    beforeImageUpload (file) {
      const isImage = file.type.startsWith('image/')
      const isLt2M = file.size / 1024 / 1024 < 2

      if (!isImage) {
        this.$message.error('上传文件只能是图片格式!')
      }
      if (!isLt2M) {
        this.$message.error('上传图片大小不能超过 2MB!')
      }
      return isImage && isLt2M
    },
    handleImageUpload (options) {
      const file = options.file
      // 使用 FileReader 将文件转为 base64
      const reader = new FileReader()
      reader.onload = (e) => {
        this.filterForm.referenceImage = e.target.result
      }
      reader.readAsDataURL(file)
    },
    startFiltering () {
      if (!this.filterForm.studentId) {
        this.$message.error('请输入学号')
        return
      }

      // 模拟过滤处理
      this.$message({
        message: '正在进行图像过滤...',
        type: 'info'
      })

      // 模拟 API 请求的延迟
      setTimeout(() => {
        // 生成模拟数据
        this.generateMockFilterResults()
        this.$message({
          message: '过滤完成，找到 ' + this.filterResults.length + ' 条匹配记录',
          type: 'success'
        })
      }, 2000)
    },
    generateMockFilterResults () {
      // 清空之前的结果
      this.filterResults = []

      // 生成 3-8 条随机匹配记录
      const resultCount = Math.floor(Math.random() * 6) + 3

      for (let i = 0; i < resultCount; i++) {
        // 随机选择摄像头
        const cameraIndex = Math.floor(Math.random() * this.cameras.length)
        const camera = this.cameras[cameraIndex]

        // 随机生成匹配的属性
        const matchedAttributes = []
        if (this.filterForm.attributes.includes('umbrella') && Math.random() > 0.5) {
          matchedAttributes.push('雨伞')
        }
        if (this.filterForm.attributes.includes('backpack') && Math.random() > 0.3) {
          matchedAttributes.push('背包')
        }
        if (this.filterForm.attributes.includes('hat') && Math.random() > 0.7) {
          matchedAttributes.push('帽子')
        }
        if (this.filterForm.attributes.includes('glasses') && Math.random() > 0.6) {
          matchedAttributes.push('眼镜')
        }

        // 生成随机时间戳
        const startTime = new Date(this.filterForm.timeRange[0]).getTime()
        const endTime = new Date(this.filterForm.timeRange[1]).getTime()
        const randomTime = new Date(startTime + Math.random() * (endTime - startTime))

        // 添加到结果中
        this.filterResults.push({
          id: i + 1,
          studentId: this.filterForm.studentId,
          cameraId: camera.id,
          location: camera.location,
          timestamp: randomTime.toLocaleString(),
          matchedAttributes: matchedAttributes,
          // 使用占位图像，实际应用中应为真实图像
          image: `https://picsum.photos/id/${(i + 10) * 10}/300/200`
        })
      }

      // 按时间排序
      this.filterResults.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    },
    startReId () {
      // 重置进度
      this.reIdProgress = {
        spatialTemporal: 0,
        crossCamera: 0,
        featureMatching: 0,
        trajectoryIntegration: 0
      }

      this.$message({
        message: '正在执行重识别...',
        type: 'info'
      })

      // 模拟时空约束过滤
      this.simulateProgress('spatialTemporal', 2000, () => {
        // 模拟跨摄像头匹配
        this.simulateProgress('crossCamera', 1500, () => {
          // 模拟特征提取与匹配
          this.simulateProgress('featureMatching', 2500, () => {
            // 模拟轨迹整合
            this.simulateProgress('trajectoryIntegration', 1000, () => {
              // 生成重识别结果
              this.generateMockReIdResults()
              this.$message({
                message: '重识别完成',
                type: 'success'
              })
            })
          })
        })
      })
    },
    simulateProgress (key, duration, callback) {
      const startTime = Date.now()
      const interval = 100 // 更新间隔

      const updateProgress = () => {
        const elapsed = Date.now() - startTime
        const progress = Math.min(Math.floor((elapsed / duration) * 100), 100)
        this.reIdProgress[key] = progress

        if (progress < 100) {
          setTimeout(updateProgress, interval)
        } else {
          if (callback) callback()
        }
      }

      updateProgress()
    },
    generateMockReIdResults () {
      // 基于过滤结果生成重识别结果
      this.reIdResults = this.filterResults.map(item => ({
        id: item.id,
        studentId: item.studentId,
        cameraId: item.cameraId,
        location: item.location,
        timestamp: item.timestamp,
        confidence: Math.floor(Math.random() * 30) + 70 // 70-99% 的置信度
      }))

      // 生成轨迹数据用于地图显示
      this.generateTrajectoryData()
    },
    generateTrajectoryData () {
      // 从重识别结果生成轨迹数据
      this.trajectoryData = {
        points: [],
        cameras: []
      }

      // 添加摄像头位置
      this.reIdResults.forEach(result => {
        const camera = this.cameras.find(c => c.id === result.cameraId)
        if (camera) {
          this.trajectoryData.cameras.push({
            id: camera.id,
            name: camera.name,
            position: camera.position,
            timestamp: result.timestamp
          })
        }
      })

      // 根据摄像头位置生成轨迹点
      for (let i = 0; i < this.trajectoryData.cameras.length; i++) {
        const camera = this.trajectoryData.cameras[i]

        // 添加摄像头所在位置
        this.trajectoryData.points.push({
          position: camera.position,
          type: 'camera',
          cameraId: camera.id
        })

        // 如果不是最后一个摄像头，添加到下一个摄像头的路径点
        if (i < this.trajectoryData.cameras.length - 1) {
          const nextCamera = this.trajectoryData.cameras[i + 1]
          const startPos = camera.position
          const endPos = nextCamera.position

          // 生成几个中间点，模拟行走轨迹
          const pointCount = Math.floor(Math.random() * 3) + 2
          for (let j = 1; j <= pointCount; j++) {
            const ratio = j / (pointCount + 1)
            const lat = startPos[1] + (endPos[1] - startPos[1]) * ratio
            const lng = startPos[0] + (endPos[0] - startPos[0]) * ratio

            // 添加一点随机偏移，使路径看起来更自然
            const offsetLat = (Math.random() - 0.5) * 0.0005
            const offsetLng = (Math.random() - 0.5) * 0.0005

            this.trajectoryData.points.push({
              position: [lng + offsetLng, lat + offsetLat],
              type: 'path'
            })
          }
        }
      }
    },
    handleCanPlay () {
      const videoPlayer = this.$refs.videoPlayer
      if (videoPlayer && videoPlayer.paused) {
        videoPlayer.play().catch(e => {
          console.log('视频播放失败:', e)
          this.$message({
            message: '请点击视频进行播放',
            type: 'info'
          })
        })
      }
    },
    handleCameraClick (cameraId) {
      // 查找对应的摄像头数据和结果
      const camera = this.cameras.find(c => c.id === cameraId)
      const result = this.reIdResults.find(r => r.cameraId === cameraId)
      if (!camera || !result) return

      // 设置视频信息 - 修改视频路径
      this.selectedVideo = {
        url: 'target.mp4', // 不使用前导斜杠，避免路径解析问题
        cameraId: camera.id,
        location: camera.location,
        timestamp: result.timestamp
      }

      this.showVideo = true

      // 确保视频元素已加载
      this.$nextTick(() => {
        if (this.$refs.videoPlayer) {
          // 移除load()调用，避免中断play()请求
          this.$refs.videoPlayer.play().catch(e => {
            console.error('视频播放失败:', e)
            this.$message({
              message: '请点击视频进行播放',
              type: 'info'
            })
          })
        }
      })
    },
    closeVideo () {
      if (this.$refs.videoPlayer) {
        this.$refs.videoPlayer.pause()
      }
      this.showVideo = false
    },
    calculateTrajectoryLength () {
      let length = 0
      const points = this.trajectoryData.points

      for (let i = 1; i < points.length; i++) {
        const prev = points[i - 1]
        const curr = points[i]
        // 使用简单的欧几里得距离计算，实际应使用地球表面距离计算
        const dx = (curr.position[0] - prev.position[0]) * 111000 * Math.cos(prev.position[1] * Math.PI / 180)
        const dy = (curr.position[1] - prev.position[1]) * 111000
        length += Math.sqrt(dx * dx + dy * dy)
      }

      return Math.round(length)
    },
    calculateTotalTime () {
      if (this.reIdResults.length < 2) return '0分钟'

      const firstTime = new Date(this.reIdResults[0].timestamp)
      const lastTime = new Date(this.reIdResults[this.reIdResults.length - 1].timestamp)
      const diffMinutes = Math.round((lastTime - firstTime) / (1000 * 60))

      if (diffMinutes < 60) {
        return `${diffMinutes}分钟`
      } else {
        const hours = Math.floor(diffMinutes / 60)
        const minutes = diffMinutes % 60
        return `${hours}小时${minutes > 0 ? ` ${minutes}分钟` : ''}`
      }
    },
    getTimelineColor (index) {
      const colors = ['#409EFF', '#67C23A', '#E6A23C', '#F56C6C', '#909399']
      return colors[index % colors.length]
    },
    prevStep () {
      if (this.activeStep > 1) {
        this.activeStep--
      }
    },
    nextStep () {
      if (this.activeStep < 3) {
        if (this.activeStep === 1 && this.filterResults.length === 0) {
          this.$message.warning('请先完成过滤操作')
          return
        }
        if (this.activeStep === 2 && this.reIdResults.length === 0) {
          this.$message.warning('请先完成重识别处理')
          return
        }
        this.activeStep++
      } else {
        // 完成
        this.$message({
          message: '轨迹可视化完成',
          type: 'success'
        })
      }
    }
  }
}
</script>

<style scoped>
@import "../static/css/mediaTracking.css";

.container {
  background: url("../assets/bg5.jpg") no-repeat center;
  background-size: 100% 100%;
  min-height: 100vh;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.title {
  font-size: 2.5vw;
  color: #5485c2;
  margin-bottom: 20px;
  text-align: center;
}

.steps-container {
  width: 80%;
  margin: 0 auto 30px;
}

.content {
  display: flex;
  flex: 1;
  margin-bottom: 30px;
}

.content-left {
  flex: 3;
  margin-right: 20px;
}

.content-right {
  flex: 1;
}

.baidu-map {
  width: 100%;
  height: 70vh;
  border-radius: 4px;
  overflow: hidden;
}

/* 添加滚动条样式 */
.card {
  margin-bottom: 20px;
  overflow-y: auto; /* 垂直滚动条 */
  max-height: 400px; /* 设置最大高度，超出时显示滚动条 */
}

.input-card, .reid-card {
  height: 100%;
  overflow-y: auto; /* 垂直滚动条 */
}

.filter-results, .reid-results, .track-info {
  overflow-y: auto; /* 垂直滚动条 */
  max-height: 300px; /* 设置最大高度 */
}

.timeline {
  padding: 10px;
  max-height: 400px; /* 设置最大高度 */
  overflow-y: auto; /* 垂直滚动条 */
}

.video-player {
  width: 100%;
}

.video-container {
  width: 100%;
  margin-bottom: 10px;
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
}

.video-element {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
}

.video-info {
  font-size: 14px;
  color: #666;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 5px;
}

.legend-color {
  width: 15px;
  height: 15px;
  margin-right: 5px;
  border-radius: 50%;
}

.nav-buttons {
  margin-top: 20px;
  text-align: center;
}

.upload-demo {
  margin-top: 10px;
}

.reference-image {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
}

.no-results {
  text-align: center;
  color: #999;
}

.result-item {
  display: flex;
  align-items: center;
}

.result-image {
  width: 80px;
  height: 80px;
  object-fit: cover;
  border-radius: 4px;
  margin-right: 10px;
}

.result-info {
  flex: 1;
}

.progress-item {
  margin-bottom: 10px;
}

.progress-label {
  font-size: 14px;
  margin-bottom: 5px;
}

.reid-options {
  margin-top: 20px;
}

.reid-progress {
  margin-bottom: 20px;
}

.student-info {
  font-size: 14px;
  color: #333;
}

.trajectory-legend {
  margin-top: 10px;
}

.trajectory-legend .legend-item {
  margin-bottom: 0;
}

.trajectory-legend .legend-color {
  width: 15px;
  height: 15px;
  margin-right: 5px;
  border-radius: 50%;
}

</style>
