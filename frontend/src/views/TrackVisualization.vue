<template>
  <div class="container">
    <Menu></Menu>

    <el-steps :active="activeStep" finish-status="success" class="steps-container" align-center>
      <el-step title="身份和属性过滤" class="custom-step"></el-step>
      <el-step title="重识别处理" class="custom-step"></el-step>
      <el-step title="学生轨迹追踪" class="custom-step"></el-step>
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
                <el-checkbox label="bicycle">自行车</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="参考图片">
              <div class="image-upload-area">
                <el-upload
                  class="upload-demo"
                  action="#"
                  :http-request="handleImageUpload"
                  :show-file-list="false"
                  :before-upload="beforeImageUpload">
                  <img v-if="filterForm.referenceImage" :src="filterForm.referenceImage" class="reference-image">
                  <el-button v-else type="primary">点击上传参考图片</el-button>
                </el-upload>
                <div class="el-upload__tip">请上传清晰的正面照片，用于辅助识别</div>
              </div>
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
                  <!--<img :src="item.image" class="result-image"> -->
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
              <span class="progress-label">特征提取</span>
              <el-progress :percentage="reIdProgress.featureMatching" :status="reIdProgress.featureMatching === 100 ? 'success' : ''"></el-progress>
            </div>
            <div class="progress-item">
              <span class="progress-label">跨摄像头匹配</span>
              <el-progress :percentage="reIdProgress.crossCamera" :status="reIdProgress.crossCamera === 100 ? 'success' : ''"></el-progress>
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
                  <el-option label="AGWReID" value="agw"></el-option>
                  <el-option label="MGNReID" value="mgn"></el-option>
                  <el-option label="SBSReID" value="sbs"></el-option>
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
    <div v-if="activeStep === 3" class="content trajectory-content">
    <div class="content-left map-container">
      <BaiduMap
        class="baidu-map"
        ref="baiduMap"
        :trajectory-data="trajectoryData"
        @camera-click="handleCameraClick">
      </BaiduMap>
    </div>
    <div class="content-right info-container">
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
import io from 'socket.io-client'
import {filterRecords, analyzeSpacetimeConstraints, extractFeatures, matchFeatures} from '../api/api'
import axios from 'axios'

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
        algorithm: 'mgn',
        threshold: 80
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
      // 摄像头数据
      cameras: [],
      // 存储视频URL的基础路径
      baseVideoUrl: '',
      socket: null,
      isLoading: false,
      recordIds: []
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
      if (!this.selectedVideo.url) return ''

      // 如果已经是完整的URL，则直接返回
      if (this.selectedVideo.url.match(/^(http|https|file):\/\//)) {
        return this.selectedVideo.url
      }

      // 处理相对路径
      return this.selectedVideo.url // Vue会正确处理相对于public目录的路径
    }
  },
  created () {
    // 获取基础URL，用于正确构建资源路径
    this.baseVideoUrl = process.env.BASE_URL || ''
    // 连接WebSocket
    this.connectSocket()
  },
  mounted () {
    // 监听ReID进度更新
    if (this.socket) {
      this.socket.on('reid_progress', (data) => {
        if (data.stage === 'spatialTemporal') {
          this.reIdProgress.spatialTemporal = data.percentage
        } else if (data.stage === 'featureMatching') {
          this.reIdProgress.featureMatching = data.percentage
        } else if (data.stage === 'crossCamera') {
          this.reIdProgress.crossCamera = data.percentage
        } else if (data.stage === 'trajectoryIntegration') {
          this.reIdProgress.trajectoryIntegration = data.percentage
        }
      })
    }
  },
  beforeDestroy () {
    if (this.socket) {
      this.socket.disconnect()
    }
  },
  methods: {
    connectSocket () {
      // 连接到WebSocket服务器
      const serverUrl = process.env.VUE_APP_API_URL || 'http://localhost:5000'
      this.socket = io(serverUrl)

      this.socket.on('connect', () => {
        console.log('WebSocket连接成功')
      })

      this.socket.on('connect_error', (error) => {
        console.error('WebSocket连接失败:', error)
      })
    },
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
    async startFiltering () {
      if (!this.filterForm.studentId && this.filterForm.timeRange.length === 0 && this.filterForm.attributes.length === 0) {
        this.$message.error('请至少输入一个过滤条件')
        return
      }

      this.isLoading = true
      this.$message({
        message: '正在进行数据过滤...',
        type: 'info'
      })

      try {
        // 不使用 toISOString()，改为手动构建带有本地时区偏移的时间字符串
        const formatLocalTime = (date) => {
          return date.getFullYear() + '-' +
         String(date.getMonth() + 1).padStart(2, '0') + '-' +
         String(date.getDate()).padStart(2, '0') + 'T' +
         String(date.getHours()).padStart(2, '0') + ':' +
         String(date.getMinutes()).padStart(2, '0') + ':' +
         String(date.getSeconds()).padStart(2, '0')
        }

        // 准备请求参数
        const requestData = {
          studentId: this.filterForm.studentId || null,
          startTime: this.filterForm.timeRange[0] ? formatLocalTime(new Date(this.filterForm.timeRange[0])) : null,
          endTime: this.filterForm.timeRange[1] ? formatLocalTime(new Date(this.filterForm.timeRange[1])) : null,
          attributes: {},
          image_base64: this.filterForm.referenceImage
        }

        // 处理属性过滤
        if (this.filterForm.attributes.includes('umbrella')) {
          requestData.attributes.has_umbrella = true
        }
        if (this.filterForm.attributes.includes('backpack')) {
          requestData.attributes.has_backpack = true
        }
        if (this.filterForm.attributes.includes('bicycle')) {
          requestData.attributes.has_bicycle = true
        }

        // 如果有参考图片，添加到请求中
        if (this.filterForm.referenceImage) {
          requestData.referenceImage = this.filterForm.referenceImage
        }

        // 调用API
        const response = await filterRecords(requestData)

        if (response.data.status === 'success') {
          // 处理返回的过滤结果并确保按时间排序
          this.filterResults = response.data.data.map(record => {
            return {
              id: record.id,
              studentId: record.student_id,
              cameraId: record.camera_id.toString(),
              name: record.name || `摄像头${record.camera_id}`,
              timestamp: record.timestamp,
              matchedAttributes: this.getMatchedAttributes(record),
              // image: record.image_base64 || `https://picsum.photos/id/${record.id * 10}/300/200`,
              has_backpack: record.has_backpack,
              has_umbrella: record.has_umbrella,
              has_bicycle: record.has_bicycle
            }
          })

          // 确保按时间排序
          this.filterResults.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

          if (this.filterResults.length > 0) {
            this.$message.success(`找到 ${this.filterResults.length} 条匹配记录`)
          } else {
            this.$message.warning('未找到匹配记录')
          }
        } else {
          this.$message.error(response.data.message || '过滤请求失败')
        }
      } catch (error) {
        console.error('过滤请求错误:', error)
        this.$message.error('过滤请求失败，请检查网络连接')
      } finally {
        this.isLoading = false
      }
    },

    // 辅助函数，从记录中获取匹配的属性
    getMatchedAttributes (record) {
      const attributes = []
      if (record.has_umbrella) attributes.push('雨伞')
      if (record.has_backpack) attributes.push('背包')
      if (record.has_bicycle) attributes.push('自行车')
      return attributes
    },

    async startReId () {
      // 重置进度
      this.reIdProgress = {
        spatialTemporal: 0,
        crossCamera: 0,
        featureMatching: 0,
        trajectoryIntegration: 0
      }

      // 平滑动画相关参数
      const animationSpeed = {
        fast: 10, // 快速任务每步增加的百分比
        slow: 2 // 缓慢任务每步增加的百分比
      }
      let animationIntervals = {
        spatialTemporal: null,
        crossCamera: null,
        featureMatching: null,
        trajectoryIntegration: null
      }

      // 创建进度条动画函数
      const animateProgress = (progressKey, targetValue, isSlowTask = false) => {
        // 如果已有动画正在进行，先清除
        if (animationIntervals[progressKey]) {
          clearInterval(animationIntervals[progressKey])
        }

        const step = isSlowTask ? animationSpeed.slow : animationSpeed.fast
        // 最大值设为目标值-1，留出后端完成时的最后一步
        const maxAnimationValue = isSlowTask ? Math.min(targetValue, 85) : targetValue - 5

        animationIntervals[progressKey] = setInterval(() => {
          if (this.reIdProgress[progressKey] >= maxAnimationValue) {
            clearInterval(animationIntervals[progressKey])
            animationIntervals[progressKey] = null
          } else {
            this.reIdProgress[progressKey] += step
          }
        }, 100)

        // 返回一个用于完成进度的函数
        return () => {
          if (animationIntervals[progressKey]) {
            clearInterval(animationIntervals[progressKey])
            animationIntervals[progressKey] = null
          }

          // 平滑过渡到目标值
          const finalAnimation = setInterval(() => {
            if (this.reIdProgress[progressKey] >= targetValue) {
              this.reIdProgress[progressKey] = targetValue
              clearInterval(finalAnimation)
            } else {
              this.reIdProgress[progressKey] += Math.max(1, (targetValue - this.reIdProgress[progressKey]) / 3)
            }
          }, 80)
        }
      }

      // 清除所有动画
      const clearAllAnimations = () => {
        Object.keys(animationIntervals).forEach(key => {
          if (animationIntervals[key]) {
            clearInterval(animationIntervals[key])
            animationIntervals[key] = null
          }
        })
      }

      this.isLoading = true
      this.$message({
        message: '开始进行时空约束分析...',
        type: 'info'
      })

      try {
        // 开始时空约束分析动画
        const completeSpatialTemporalProgress = animateProgress('spatialTemporal', 100)

        // 第一步：时空约束分析
        const spatiotemporalRequestData = {
          records: this.filterResults.map(record => {
            const cameraId = parseInt(record.cameraId)
            return {
              id: record.id,
              student_id: record.studentId || null,
              camera_id: isNaN(cameraId) ? null : cameraId,
              timestamp: record.timestamp,
              name: record.name || null,
              has_backpack: record.has_backpack,
              has_umbrella: record.has_umbrella,
              has_bicycle: record.has_bicycle
            }
          })
        }

        console.log('发送到时空约束分析的数据:', spatiotemporalRequestData)

        // 检查是否所有记录都有有效的摄像头ID
        if (spatiotemporalRequestData.records.some(r => r.camera_id === null)) {
          this.$message.warning('部分记录缺少有效的摄像头ID，这可能影响分析结果')
        }

        // 调用时空约束分析API
        const spatiotemporalResponse = await analyzeSpacetimeConstraints(spatiotemporalRequestData)

        if (spatiotemporalResponse.data.status === 'success') {
          // 更新过滤结果为时空约束过滤后的结果
          const filteredRecords = spatiotemporalResponse.data.data.map(record => {
            return {
              id: record.id,
              student_id: record.student_id,
              camera_id: parseInt(record.camera_id),
              timestamp: record.timestamp,
              name: record.name,
              has_backpack: record.has_backpack,
              has_umbrella: record.has_umbrella,
              has_bicycle: record.has_bicycle,
              location_x: record.location_x,
              location_y: record.location_y
            }
          })

          this.filterResults = filteredRecords
          console.log('时空约束分析后的结果:', this.filterResults)

          // 完成时空约束分析进度
          completeSpatialTemporalProgress()

          // 确保时空约束分析进度显示100%后再显示下一步提示信息
          setTimeout(() => {
            this.$message.success(`时空约束分析完成，保留 ${this.filterResults.length} 条有效记录`)

            // 第二步：特征提取
            this.$message({
              message: '开始进行特征提取...',
              type: 'info'
            })

            // 开始特征提取进度动画（慢速）
            // const completeFeatureMatchingProgress = animateProgress('featureMatching', 100, true)

            // 准备特征提取请求数据
            const extractFeaturesRequestData = {
              records: this.filterResults.map(record => ({
                id: record.id,
                student_id: record.student_id,
                camera_id: record.camera_id,
                timestamp: record.timestamp,
                location_x: record.location_x,
                location_y: record.location_y,
                name: record.name || `摄像头${record.camera_id}`
              })),
              algorithm: this.reIdOptions.algorithm
            }

            if (this.filterForm.referenceImage) {
              extractFeaturesRequestData.records.unshift({
                id: 'query', // 使用特殊ID标识查询记录
                image_base64: this.filterForm.referenceImage // 使用已经转为base64的图像数据
              })
            }

            console.log('发送到特征提取的数据:', extractFeaturesRequestData)

            // 执行特征提取
            extractFeatures(extractFeaturesRequestData).then(extractResponse => {
              if (extractResponse.data.status === 'success') {
                // 完成特征提取进度
                // completeFeatureMatchingProgress()

                // 获取提取的特征记录和帧特征
                const featuresRecords = extractResponse.data.features_records
                const allFramesFeatures = extractResponse.data.all_frames_features || {}
                const queryFeature = extractResponse.data.query_feature

                console.log('特征提取完成，获取到特征记录:', featuresRecords)
                console.log('获取到帧特征数据:', allFramesFeatures)

                // 确保特征提取进度完成后再显示下一步
                setTimeout(() => {
                  this.$message({
                    message: '特征提取完成，开始进行跨摄像头匹配...',
                    type: 'info'
                  })

                  // 开始跨摄像头匹配进度动画
                  const completeCrossCameraProgress = animateProgress('crossCamera', 100)

                  // 第三步：特征匹配
                  const matchFeaturesRequestData = {
                    records: featuresRecords,
                    all_frames_features: allFramesFeatures,
                    query_feature: queryFeature,
                    threshold: this.reIdOptions.threshold / 100 // 将百分比转换为0-1的值
                  }

                  console.log('发送到特征匹配的数据:', matchFeaturesRequestData)

                  // 执行特征匹配
                  matchFeatures(matchFeaturesRequestData).then(matchResponse => {
                    if (matchResponse.data.status === 'success') {
                      // 完成跨摄像头匹配进度
                      completeCrossCameraProgress()

                      // 更新重识别结果
                      this.reIdResults = matchResponse.data.matched_records.map(record => {
                        // 计算帧级匹配的统计信息
                        const frameMatches = record.matched_frames || []
                        const frameMatchCount = frameMatches.length
                        const avgFrameConfidence = frameMatches.length > 0
                          ? frameMatches.reduce((sum, frame) => sum + frame.similarity, 0) / frameMatches.length
                          : 0

                        return {
                          id: record.id,
                          studentId: record.student_id,
                          cameraId: record.camera_id,
                          timestamp: record.timestamp,
                          name: record.name,
                          location_x: record.location_x,
                          location_y: record.location_y,
                          confidence: record.confidence,
                          videoPath: record.video_path || null,
                          videoStartTime: record.video_start_time || null,
                          videoEndTime: record.video_end_time || null,
                          frameMatches: frameMatches,
                          frameMatchCount: frameMatchCount,
                          avgFrameConfidence: avgFrameConfidence
                        }
                      })

                      // 保存原始匹配数据，用于详细查看
                      this.rawMatchData = matchResponse.data.matched_records

                      setTimeout(() => {
                        // 第四步：构建最可能的轨迹
                        this.$message({
                          message: '生成最佳轨迹...',
                          type: 'info'
                        })

                        // 开始轨迹整合进度动画
                        const completeTrajectoryProgress = animateProgress('trajectoryIntegration', 100)

                        if (this.reIdResults.length > 0) {
                          // 按时间排序
                          this.reIdResults.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

                          // 提取轨迹记录ID
                          this.recordIds = this.reIdResults.map(record => record.id)

                          // 使用重识别结果生成轨迹数据
                          // 构建轨迹数据格式
                          const trajectoryData = this.reIdResults.map(record => ({
                            id: record.id,
                            camera_id: record.cameraId,
                            timestamp: record.timestamp,
                            location_x: record.location_x,
                            location_y: record.location_y,
                            name: record.name || `摄像头${record.cameraId}`
                          }))

                          // 简单模拟轨迹段，连接相邻摄像头点
                          const segments = []
                          for (let i = 0; i < trajectoryData.length - 1; i++) {
                            segments.push({
                              start_location: [trajectoryData[i].location_x, trajectoryData[i].location_y],
                              end_location: [trajectoryData[i + 1].location_x, trajectoryData[i + 1].location_y],
                              start_camera_id: trajectoryData[i].camera_id,
                              end_camera_id: trajectoryData[i + 1].camera_id,
                              start_time: trajectoryData[i].timestamp,
                              end_time: trajectoryData[i + 1].timestamp
                            })
                          }

                          // 暂无异常点数据
                          const anomalies = []

                          // 处理轨迹数据
                          this.processTrajectoryData(trajectoryData, segments, anomalies)

                          // 轨迹集成完成
                          completeTrajectoryProgress()

                          setTimeout(() => {
                            this.$message.success(`重识别完成，找到 ${this.reIdResults.length} 条匹配记录`)
                            this.isLoading = false
                          }, 500)
                        } else {
                          this.recordIds = []
                          completeTrajectoryProgress()

                          setTimeout(() => {
                            this.$message.warning('重识别处理完成，但未找到匹配记录')
                            this.isLoading = false
                          }, 500)
                        }
                      }, 500) // 确保跨摄像头匹配进度显示100%后再进行下一步
                    } else {
                      clearAllAnimations()
                      this.$message.error(matchResponse.data.message || '特征匹配失败')
                      this.isLoading = false
                    }
                  }).catch(error => {
                    clearAllAnimations()
                    console.error('特征匹配错误:', error)
                    this.$message.error('特征匹配失败，请检查网络连接')
                    this.isLoading = false
                  })
                }, 500) // 确保特征提取进度完成后再进行下一步
              } else {
                clearAllAnimations()
                this.$message.error(extractResponse.data.message || '特征提取失败')
                this.isLoading = false
              }
            }).catch(error => {
              clearAllAnimations()
              console.error('特征提取错误:', error)
              this.$message.error('特征提取失败，请检查网络连接')
              this.isLoading = false
            })
          }, 500) // 确保时空约束分析进度显示100%后再进行下一步
        } else {
          clearAllAnimations()
          this.$message.error(spatiotemporalResponse.data.message || '时空约束分析失败')
          this.isLoading = false
        }
      } catch (error) {
        clearAllAnimations()
        console.error('重识别处理错误:', error)
        this.$message.error('重识别处理失败，请检查网络连接')
        this.isLoading = false
      }
    },

    processTrajectoryData (trajectoryData, segments, anomalies) {
      // 从后端数据构建地图组件所需的轨迹数据格式
      this.trajectoryData = {
        points: [],
        cameras: []
      }

      // 确保轨迹数据按时间排序
      const sortedTrajectoryData = [...trajectoryData].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))

      console.log('处理轨迹数据，摄像头记录数:', sortedTrajectoryData.length)

      // 添加摄像头位置
      sortedTrajectoryData.forEach(record => {
        // 检查是否已添加该摄像头
        const cameraId = record.camera_id.toString()
        if (!this.trajectoryData.cameras.some(c => c.id === cameraId)) {
          this.trajectoryData.cameras.push({
            id: cameraId,
            name: record.name || `摄像头${cameraId}`,
            position: [record.location_x, record.location_y],
            timestamp: record.timestamp
          })
        }
      })

      console.log('添加了摄像头数:', this.trajectoryData.cameras.length)

      // 按时间顺序添加摄像头点
      this.trajectoryData.cameras.forEach(camera => {
        sortedTrajectoryData.find(r => r.camera_id.toString() === camera.id)
        this.trajectoryData.points.push({
          position: camera.position,
          type: 'camera',
          cameraId: camera.id,
          timestamp: camera.timestamp,
          order: sortedTrajectoryData.findIndex(r => r.camera_id.toString() === camera.id) // 添加顺序属性
        })
      })

      // 添加中间路径点
      if (segments && segments.length > 0) {
        segments.forEach((segment, segmentIndex) => {
          const startPos = segment.start_location
          const endPos = segment.end_location
          const startTime = new Date(segment.start_time)
          const endTime = new Date(segment.end_time)

          // 在起点和终点之间生成几个中间点模拟路径
          const pointCount = Math.floor(Math.random() * 3) + 2
          for (let j = 1; j <= pointCount; j++) {
            const ratio = j / (pointCount + 1)
            const x = startPos[0] + (endPos[0] - startPos[0]) * ratio
            const y = startPos[1] + (endPos[1] - startPos[1]) * ratio

            // 插值计算中间时间点
            const timeOffset = (endTime - startTime) * ratio
            const pointTime = new Date(startTime.getTime() + timeOffset)

            // 添加轻微随机偏移使路径更自然
            const offsetX = (Math.random() - 0.5) * 0.0002
            const offsetY = (Math.random() - 0.5) * 0.0002

            this.trajectoryData.points.push({
              position: [x + offsetX, y + offsetY],
              type: 'path',
              order: segmentIndex + 0.1 * j, // 使用分数顺序保证中间点在相应的摄像头点之间
              timestamp: pointTime.toISOString()
            })
          }
        })
      }

      // 添加异常点标记(如果有)
      if (anomalies && anomalies.length > 0) {
        anomalies.forEach(anomaly => {
          if (anomaly.location) {
            this.trajectoryData.points.push({
              position: [anomaly.location[0], anomaly.location[1]],
              type: 'anomaly',
              order: 1000 // 给异常点一个很大的顺序值，确保它们最后渲染
            })
          }
        })
      }

      // 按顺序排序所有点
      this.trajectoryData.points.sort((a, b) => a.order - b.order)

      console.log('处理后的轨迹数据:', this.trajectoryData)
    },

    handleCameraClick (cameraId) {
      // 查找对应的摄像头结果
      const result = this.reIdResults.find(r => r.cameraId.toString() === cameraId.toString())
      if (!result) {
        console.error(`未找到摄像头ID为${cameraId}的结果`)
        this.$message.warning(`未找到摄像头${cameraId}对应的视频数据`)
        return
      }

      console.log(`点击摄像头${cameraId}，找到对应结果:`, result)

      // 判断视频路径类型并正确构建
      let videoUrl
      if (result.videoPath) {
        // 如果是阿里云OSS链接，直接使用
        if (result.videoPath.startsWith('https://qingwu-oss.oss-cn-heyuan.aliyuncs.com/')) {
          videoUrl = result.videoPath
          console.log('使用阿里云OSS视频链接:', videoUrl)
          // eslint-disable-next-line brace-style
        }
        // 如果是其他HTTP(S)链接
        else if (result.videoPath.startsWith('http')) {
          videoUrl = result.videoPath
          console.log('使用HTTP(S)视频链接:', videoUrl)
        }
      } else {
        // 无视频路径情况
        this.$message.warning(`摄像头${cameraId}没有关联视频`)
        return
      }

      // 设置视频信息
      this.selectedVideo = {
        url: videoUrl,
        cameraId: cameraId,
        timestamp: result.timestamp,
        location: result.name || `位置${cameraId}`,
        startTime: result.videoStartTime,
        endTime: result.videoEndTime
      }

      this.showVideo = true

      // 确保视频元素已加载
      this.$nextTick(() => {
        if (this.$refs.videoPlayer) {
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

    calculateTrajectoryLength () {
      let length = 0
      const cameraPoints = this.trajectoryData.points.filter(p => p.type === 'camera')

      // 按时间顺序排序摄像头点
      cameraPoints.sort((a, b) => {
        if (a.timestamp && b.timestamp) {
          return new Date(a.timestamp) - new Date(b.timestamp)
        }
        return a.order - b.order
      })

      // 计算相邻摄像头点之间的距离
      for (let i = 1; i < cameraPoints.length; i++) {
        const prev = cameraPoints[i - 1]
        const curr = cameraPoints[i]

        // 使用哈弗辛公式计算地球表面距离(以米为单位)
        const lat1 = prev.position[1] * Math.PI / 180
        const lat2 = curr.position[1] * Math.PI / 180
        const lon1 = prev.position[0] * Math.PI / 180
        const lon2 = curr.position[0] * Math.PI / 180

        const R = 6371000 // 地球半径，单位米
        const dLat = lat2 - lat1
        const dLon = lon2 - lon1

        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1) * Math.cos(lat2) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2)
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
        const distance = R * c

        length += distance
      }

      return Math.round(length)
    },

    calculateTotalTime () {
      if (this.reIdResults.length < 2) return '0分钟'

      // 按时间排序
      const sortedResults = [...this.reIdResults].sort((a, b) =>
        new Date(a.timestamp) - new Date(b.timestamp)
      )

      const firstTime = new Date(sortedResults[0].timestamp)
      const lastTime = new Date(sortedResults[sortedResults.length - 1].timestamp)
      const diffMilliseconds = lastTime - firstTime
      const diffMinutes = Math.round(diffMilliseconds / (1000 * 60))

      if (diffMinutes < 60) {
        return `${diffMinutes}分钟`
      } else {
        const hours = Math.floor(diffMinutes / 60)
        const minutes = diffMinutes % 60
        return `${hours}小时${minutes > 0 ? ` ${minutes}分钟` : ''}`
      }
    },

    handleCanPlay () {
      // 视频加载完成后自动播放
      if (this.$refs.videoPlayer) {
        this.$refs.videoPlayer.play().catch(e => {
          console.error('视频播放失败:', e)
          this.$message({
            message: '请点击视频进行播放',
            type: 'info'
          })
        })
      }
    },

    closeVideo () {
      this.showVideo = false
      if (this.$refs.videoPlayer) {
        this.$refs.videoPlayer.pause()
        this.$refs.videoPlayer.currentTime = 0 // 重置视频时间
      }
    },

    getTimelineColor (index) {
      // 根据索引返回不同的颜色
      const colors = ['#67C23A', '#E6A23C', '#409EFF', '#F56C6C']
      return colors[index % colors.length]
    },

    prevStep () {
      if (this.activeStep > 1) {
        this.activeStep--
      }
    },

    nextStep () {
      if (this.activeStep < 3) {
        this.activeStep++
      } else if (this.activeStep === 3) {
        // 构建轨迹数据
        const trajectoryData = {
          studentId: this.filterForm.studentId,
          timeRange: this.filterForm.timeRange,
          traversedCameras: this.traversedCameras,
          trajectoryLength: this.calculateTrajectoryLength(),
          totalTime: this.calculateTotalTime(),
          trajectoryPoints: this.trajectoryData.points,
          cameras: this.trajectoryData.cameras
        }

        // 发送请求保存轨迹数据
        axios.post('/api/trajectories', trajectoryData)
          .then(response => {
            if (response.data.success) {
              this.$message({
                message: '轨迹数据保存成功',
                type: 'success'
              })
            } else {
              this.$message.warning('轨迹数据保存失败')
            }
          })
          .catch(error => {
            console.error('保存轨迹数据错误:', error)
            this.$message.error('轨迹数据保存失败，请稍后再试')
          })
      }
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
  font-size: 3vw;
  color: #5485c2;
}

.steps-container {
  margin: 20px auto 40px;
  width: 100%;
  padding: 10px 0;
}

.content {
  display: flex;
  margin-bottom: 20px;
  gap: 20px;
}

.content-left {
  flex: 2;
}

.content-right {
  flex: 1;
}

/* 确保地图填满整个区域 */
.baidu-map {
  width: 100%; /* 修改原来的120%为100% */
  height: 500px;
  border-radius: 4px;
  overflow: hidden;
}

.card {
  height: 100%;
}

.input-card {
  height: 100%;
}

.reference-image {
  width: 120px;
  height: 280px;
  object-fit: cover;
  border-radius: 4px;
  margin: 10px 0;
}

.image-upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 10px 0;
}

.filter-results {
  padding: 10px;
}

.result-count {
  margin-bottom: 10px;
  font-weight: bold;
}

.result-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}

.result-image {
  max-height: 120px;
  object-fit: cover;
  border-radius: 4px;
  margin-bottom: 10px;
}

.result-info {
  text-align: center;
}

.result-info p {
  margin: 5px 0;
}

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: #909399;
}

.no-results i {
  font-size: 48px;
  margin-bottom: 10px;
}

.nav-buttons {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.reid-card {
  height: 100%;
}

.reid-progress {
  margin-bottom: 20px;
}

.progress-item {
  margin-bottom: 15px;
}

.progress-label {
  display: block;
  margin-bottom: 5px;
}

.reid-options {
  margin-top: 20px;
}

.reid-results {
  padding: 10px;
}

.timeline {
  margin-top: 10px;
}

.track-info {
  padding: 10px;
}

.student-info {
  margin-bottom: 20px;
}

.student-info p {
  margin: 10px 0;
}

.trajectory-legend {
  border-top: 1px solid #EBEEF5;
  padding-top: 15px;
}

.legend-item {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.legend-color {
  width: 20px;
  height: 10px;
  border-radius: 2px;
  margin-right: 8px;
}

.video-player {
  padding: 10px;
}

.video-container {
  width: 100%;
  margin-bottom: 15px;
}

.video-element {
  width: 100%;
  border-radius: 4px;
}

.video-info {
  margin-top: 10px;
}

.video-info p {
  margin: 5px 0;
}
</style>
