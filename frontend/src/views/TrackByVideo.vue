<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <span>视频跟踪</span>
    </div>
    <div class="content">
      <!-- Not tracking state -->
      <div v-if="!isTracking">
        <div class="before-tracking">
          <div class="content-left">
            <div class="before-upload" v-if="!isUpload">
              <el-upload
                action="#"
                drag
                class="uploader"
                list-type="picture"
                :auto-upload="false"
                :show-file-list="false"
                :on-change="imgPreview">
                <div class="uploader-icon">
                  <i class="el-icon-upload2"></i>
                </div>
                <div class="uploader-text">请将视频拖到此处或点击上传</div>
              </el-upload>
            </div>
            <div class="after-upload" v-else>
              <video controls class="upload-img">
                <source :src="beforeTrackImgUrl" type="video/mp4" />
              </video>
            </div>
          </div>
          <div class="content-right">
            <el-card shadow="always" class="card">
              <div slot="header" class="clearfix">
                <span><b>上传跟踪视频</b></span>
              </div>
              <div v-if="!isUpload" class="step1_before_upload">
                <p>未检测到视频上传，请先在 <b>左侧</b> 上传视频</p>
              </div>
              <div v-else class="step1_after_upload">
                <el-button type="primary" round class="img-button" @click="uploadImg">开始跟踪</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </div>
      <!-- Tracking state -->
      <div class="after-tracking" v-else>
        <div class="content-left">
          <div class="detection-box">
            <el-button type="danger" @click="stopDetection" size="mini">停止检测</el-button>
          </div>
          <div class="before-success-tracking" v-if="!successTrack">
            <i class="el-icon-loading" v-if="trackStatue === 1"></i>
            <i class="el-icon-picture-outline" v-if="trackStatue === 2"></i>
          </div>
          <div class="after-success-tracking" v-else>
            <video :src="afterTrackImgUrl" controls class="upload-img"></video>
          </div>
        </div>
        <div class="content-right">
          <el-card shadow="always" class="card">
            <div slot="header" class="clearfix">
              <el-tag class="tag" v-if="trackStatue === 0" type="success">跟踪成功</el-tag>
              <el-tag class="tag" v-if="trackStatue === 1">跟踪中</el-tag>
              <el-tag class="tag" v-if="trackStatue === 2" type="danger">跟踪失败</el-tag>
            </div>
            <div class="before-success-tracking" v-if="!successTrack">
              <div class="tracking" v-if="trackStatue === 1">
                <div>
                  <el-progress class="progress" type="circle" :percentage="trackingPercentage"></el-progress>
                </div>
                <el-button type="primary" round class="cancel-btn" @click="cancelTrack">取消跟踪</el-button>
              </div>
              <div class="track-error" v-if="trackStatue === 2">
                <div>
                  <el-progress class="progress" type="circle" :percentage="trackingPercentage" status="exception"></el-progress>
                </div>
                <el-button type="primary" round class="cancel-btn" @click="tryAgain">重新跟踪</el-button>
              </div>
            </div>
            <div class="after-success-tracking" v-else>
              <div class="img-info-item">
                {{ '文件名: ' + afterTrackImg.name }}
              </div>
              <div class="img-info-item">
                {{ '类型: ' + afterTrackImg.type }}
              </div>
              <div class="img-info-item">
                {{ '文件大小: ' + trackFileSize }}
              </div>
              <el-button type="primary" round class="img-info-finish" @click="retrain">重新跟踪</el-button>
              <el-button type="primary" round class="img-info-finish" @click="downloadImg">下载视频</el-button>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import io from 'socket.io-client'
import Menu from '../components/Menu.vue'
import { trackByVideo, stopDetection } from '../api/api'

export default {
  name: 'TrackByVideo',
  components: { Menu },
  data () {
    return {
      isUpload: false,
      beforeTrackImg: '',
      afterTrackImg: '',
      beforeTrackImgUrl: '',
      afterTrackImgUrl: '',
      isTracking: false,
      successTrack: false,
      trackStatue: 1,
      trackFileSize: '',
      trackingPercentage: 0,
      stopProgress: false,
      socket: null,
      personCount: 0
    }
  },
  created () {
    this.socket = io(process.env.VUE_APP_SERVER_ADDRESS)
    this.socket.on('detection_update', (data) => {
      this.personCount = data.person_count
    })
    this.socket.on('detection_stopped', (data) => {
      this.$message({ message: '检测已停止', type: 'info' })
    })
  },
  beforeDestroy () {
    if (this.socket) {
      this.socket.disconnect()
    }
    if (this.$store && this.$store.state.cancelAxios && this.$store.state.cancelAxios.cancelAxios) {
      this.$store.state.cancelAxios.cancelAxios()
      this.$store.dispatch('delReqUrl', true)
    }
  },
  methods: {
    imgPreview (file) {
      if (file.raw.type.split('/')[0] === 'video') {
        this.beforeTrackImg = file
        this.beforeTrackImgUrl = URL.createObjectURL(file.raw)
        this.isUpload = true
      } else {
        this.$message({
          type: 'warning',
          message: '请上传正确的视频格式'
        })
      }
    },
    uploadImg () {
      if (this.beforeTrackImgUrl === '') {
        this.$message.error('请先上传视频或检查视频是否上传成功')
        return
      }
      this.isTracking = true
      this.trackStatue = 1
      this.trackingPercentage = 0
      let formData = new FormData()
      formData.append('file', this.beforeTrackImg.raw)
      trackByVideo(formData, { responseType: 'blob' }).then(res => {
        const videoBlob = new Blob([res.data], { type: 'video/mp4' })
        this.afterTrackImgUrl = URL.createObjectURL(videoBlob)
        this.trackingPercentage = 100
        this.successTrack = true
        this.trackStatue = 0
        this.$message({ message: '跟踪成功', type: 'success' })
      }).catch(err => {
        console.error(err)
        this.trackStatue = 2
        this.$message.error('跟踪失败')
      })
    },
    stopDetection () {
      stopDetection().then(() => {
        if (this.socket) this.socket.disconnect()
        this.$message({ message: '已停止检测', type: 'success' })
      }).catch(err => {
        console.error(err)
        this.$message.error('停止失败')
      })
    },
    cancelTrack () {
      this.$confirm('确认取消跟踪?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.isTracking = false
        if (this.$store && this.$store.state.cancelAxios && this.$store.state.cancelAxios.cancelAxios) {
          this.$store.state.cancelAxios.cancelAxios()
          this.$store.dispatch('delReqUrl', true)
        }
      })
    },
    retrain () {
      this.$confirm('重新跟踪将清空本次跟踪结果, 是否继续?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        this.isUpload = false
        this.isTracking = false
        this.successTrack = false
        this.beforeTrackImgUrl = ''
        this.afterTrackImgUrl = ''
        this.$message({ type: 'success', message: '操作成功' })
      })
    },
    downloadImg () {
      let a = document.createElement('a')
      a.setAttribute('href', this.afterTrackImgUrl)
      a.setAttribute('download', 'result')
      a.click()
    },
    tryAgain () {
      this.isTracking = false
      this.successTrack = false
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
.card .del-icon {
  position: absolute;
  background-color: rgba(0, 0, 0, 0);
  border: none;
  right: 1vh;
  top: 9vh;
  font-size: 4vh;
}
.detection-box {
  padding: 10px;
  border: 1px solid #ccc;
  text-align: center;
  margin-bottom: 20px;
}
</style>
