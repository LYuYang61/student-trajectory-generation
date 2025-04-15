<template>
  <div class="video-tracking-container">
    <div class="video-wrapper" ref="videoWrapper">
      <video
        ref="videoPlayer"
        class="main-video"
        @loadedmetadata="onVideoLoaded"
        @timeupdate="onTimeUpdate"
        controls>
        <source :src="videoUrl" type="video/mp4">
        您的浏览器不支持 video 标签。
      </video>

      <!-- Tracking overlay -->
      <div class="tracking-overlay" v-if="isPlaying">
        <div
          v-for="(box, index) in currentTrackingBoxes"
          :key="index"
          class="tracking-box"
          :style="{
            left: `${box.x}%`,
            top: `${box.y}%`,
            width: `${box.width}%`,
            height: `${box.height}%`,
            borderColor: box.isTarget ? '#67C23A' : '#E6A23C'
          }">
          <div class="tracking-label" :class="{ 'target-label': box.isTarget }">
            {{ box.isTarget ? '目标学生' : '其他人员' }}
          </div>
        </div>

        <!-- Trajectory paths -->
        <svg class="trajectory-svg" v-if="showTrajectory">
          <path
            v-for="(path, index) in trajectoryPaths"
            :key="`path-${index}`"
            :d="path.pathData"
            :stroke="path.isTarget ? '#67C23A' : '#E6A23C'"
            stroke-width="2"
            fill="none"
            stroke-dasharray="5,3"
            :style="{ opacity: path.isTarget ? 1 : 0.6 }">
          </path>
        </svg>
      </div>
    </div>

    <div class="controls-wrapper">
      <el-switch
        v-model="showTrajectory"
        active-text="显示轨迹"
        inactive-text="隐藏轨迹">
      </el-switch>

      <el-divider direction="vertical"></el-divider>

      <el-radio-group v-model="trackingMode" size="small">
        <el-radio-button label="all">所有人员</el-radio-button>
        <el-radio-button label="target">仅目标学生</el-radio-button>
      </el-radio-group>
    </div>

    <div class="info-panel">
      <h4>目标跟踪信息</h4>
      <p v-if="targetInfo">
        <strong>目标ID:</strong> {{ targetInfo.id }}<br>
        <strong>置信度:</strong> {{ targetInfo.confidence }}%<br>
        <strong>当前位置:</strong> ({{ targetInfo.position.x }}, {{ targetInfo.position.y }})<br>
        <strong>移动方向:</strong> {{ targetInfo.direction }}
      </p>
      <p v-else>
        未检测到目标学生
      </p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'VideoTracking',
  props: {
    videoUrl: {
      type: String,
      required: true
    },
    studentId: {
      type: String,
      required: true
    }
  },
  data () {
    return {
      isPlaying: false,
      showTrajectory: true,
      trackingMode: 'all',
      videoDuration: 0,
      currentTime: 0,

      // 模拟的跟踪数据
      trackingData: [],
      currentTrackingBoxes: [],
      trajectoryPaths: [],
      targetInfo: null
    }
  },
  watch: {
    videoUrl () {
      this.resetTracking()
      this.generateMockTrackingData()
    }
  },
  mounted () {
    this.generateMockTrackingData()
  },
  methods: {
    onVideoLoaded () {
      const video = this.$refs.videoPlayer
      if (video) {
        this.videoDuration = video.duration
      }
    },

    onTimeUpdate () {
      const video = this.$refs.videoPlayer
      if (video) {
        this.currentTime = video.currentTime
        this.isPlaying = !video.paused
        this.updateTrackingBoxes()
      }
    },

    updateTrackingBoxes () {
      // 根据当前时间更新跟踪框
      if (!this.trackingData.length) return

      // 找到当前时间最接近的帧
      const currentFrame = this.findNearestFrame(this.currentTime)
      if (!currentFrame) return

      // 更新跟踪框
      if (this.trackingMode === 'all') {
        this.currentTrackingBoxes = currentFrame.boxes
      } else {
        // 仅显示目标学生
        this.currentTrackingBoxes = currentFrame.boxes.filter(box => box.isTarget)
      }

      // 更新目标信息
      const targetBox = currentFrame.boxes.find(box => box.isTarget)
      if (targetBox) {
        this.targetInfo = {
          id: this.studentId,
          confidence: targetBox.confidence,
          position: {
            x: Math.round(targetBox.x + targetBox.width / 2),
            y: Math.round(targetBox.y + targetBox.height / 2)
          },
          direction: targetBox.direction
        }
      } else {
        this.targetInfo = null
      }

      // 更新轨迹
      this.updateTrajectories()
    },

    findNearestFrame (time) {
      // 找到最接近当前时间的帧
      if (!this.trackingData.length) return null

      let nearestFrame = null
      let minDiff = Infinity

      for (const frame of this.trackingData) {
        const diff = Math.abs(frame.timestamp - time)
        if (diff < minDiff) {
          minDiff = diff
          nearestFrame = frame
        }
      }

      return nearestFrame
    },

    updateTrajectories () {
      if (!this.showTrajectory) return

      // 清空轨迹
      this.trajectoryPaths = []

      // 计算轨迹前 2 秒到当前时间的所有点
      const startTime = Math.max(0, this.currentTime - 2)
      const relevantFrames = this.trackingData.filter(
        frame => frame.timestamp >= startTime && frame.timestamp <= this.currentTime
      )

      if (relevantFrames.length < 2) return

      // 按 ID 分组
      const trajectories = {}

      relevantFrames.forEach(frame => {
        frame.boxes.forEach(box => {
          const id = box.id
          if (!trajectories[id]) {
            trajectories[id] = {
              points: [],
              isTarget: box.isTarget
            }
          }

          // 添加中心点
          trajectories[id].points.push({
            x: box.x + box.width / 2,
            y: box.y + box.height / 2,
            timestamp: frame.timestamp
          })
        })
      })

      // 为每个 ID 生成路径
      Object.keys(trajectories).forEach(id => {
        const trajectory = trajectories[id]

        // 只在有足够点的情况下生成路径
        if (trajectory.points.length < 2) return

        // 生成 SVG 路径
        let pathData = `M ${trajectory.points[0].x} ${trajectory.points[0].y}`
        for (let i = 1; i < trajectory.points.length; i++) {
          pathData += ` L ${trajectory.points[i].x} ${trajectory.points[i].y}`
        }

        this.trajectoryPaths.push({
          pathData,
          isTarget: trajectory.isTarget
        })
      })
    },

    resetTracking () {
      this.currentTrackingBoxes = []
      this.trajectoryPaths = []
      this.targetInfo = null
    },

    generateMockTrackingData () {
      // 生成模拟的跟踪数据
      this.trackingData = []

      // 假设视频长度为 30 秒
      const videoDuration = 30

      // 每秒生成 5 帧
      const framesPerSecond = 5
      const totalFrames = videoDuration * framesPerSecond

      // 生成目标学生的运动轨迹
      const targetPath = this.generateRandomPath(totalFrames, true)

      // 生成 2-4 个其他人的运动轨迹
      const otherCount = Math.floor(Math.random() * 3) + 2
      const otherPaths = []

      for (let i = 0; i < otherCount; i++) {
        otherPaths.push(this.generateRandomPath(totalFrames, false))
      }

      // 为每一帧生成跟踪框数据
      for (let i = 0; i < totalFrames; i++) {
        const timestamp = i / framesPerSecond
        const boxes = []

        // 添加目标学生的框
        if (targetPath[i]) {
          boxes.push({
            id: 'target',
            x: targetPath[i].x,
            y: targetPath[i].y,
            width: 8 + Math.random() * 4,
            height: 16 + Math.random() * 4,
            isTarget: true,
            confidence: 85 + Math.floor(Math.random() * 15),
            direction: this.getDirection(i > 0 ? targetPath[i - 1] : null, targetPath[i])
          })
        }

        // 添加其他人的框
        otherPaths.forEach((path, index) => {
          if (path[i]) {
            boxes.push({
              id: `person-${index}`,
              x: path[i].x,
              y: path[i].y,
              width: 8 + Math.random() * 4,
              height: 16 + Math.random() * 4,
              isTarget: false,
              confidence: 70 + Math.floor(Math.random() * 20),
              direction: this.getDirection(i > 0 ? path[i - 1] : null, path[i])
            })
          }
        })

        this.trackingData.push({
          timestamp,
          boxes
        })
      }
    },

    generateRandomPath (totalFrames, isTarget) {
      const path = []

      // 为目标生成起始位置
      let x, y
      if (isTarget) {
        // 目标学生从画面边缘进入
        const edge = Math.floor(Math.random() * 4) // 0: 上, 1: 右, 2: 下, 3: 左
        switch (edge) {
          case 0: // 上边缘
            x = 20 + Math.random() * 60
            y = 0
            break
          case 1: // 右边缘
            x = 100
            y = 20 + Math.random() * 60
            break
          case 2: // 下边缘
            x = 20 + Math.random() * 60
            y = 100
            break
          case 3: // 左边缘
            x = 0
            y = 20 + Math.random() * 60
            break
        }
      } else {
        // 其他人随机位置
        x = 20 + Math.random() * 60
        y = 20 + Math.random() * 60
      }

      // 生成目标点
      let targetX = 20 + Math.random() * 60
      let targetY = 20 + Math.random() * 60

      // 每帧移动的最大距离
      const maxStepSize = 2

      // 生成路径点
      for (let i = 0; i < totalFrames; i++) {
        // 计算朝向目标点的向量
        let dx = targetX - x
        let dy = targetY - y

        // 计算向量长度
        const length = Math.sqrt(dx * dx + dy * dy)

        if (length < maxStepSize) {
          // 已经接近目标点，生成新的目标点
          const newTargetX = 20 + Math.random() * 60
          const newTargetY = 20 + Math.random() * 60

          // 添加当前点
          path.push({ x, y })

          // 更新目标点
          x = x + dx
          y = y + dy
          targetX = newTargetX
          targetY = newTargetY
        } else {
          // 朝目标点移动
          dx = dx / length * Math.min(maxStepSize, length)
          dy = dy / length * Math.min(maxStepSize, length)

          // 添加一些随机性，使路径更自然
          dx += (Math.random() - 0.5) * 0.5
          dy += (Math.random() - 0.5) * 0.5

          x += dx
          y += dy

          // 确保在画面范围内
          x = Math.max(0, Math.min(100, x))
          y = Math.max(0, Math.min(100, y))

          path.push({ x, y })
        }

        // 随机让人物短暂消失（模拟遮挡）
        if (Math.random() < 0.02) {
          // 2% 的概率消失 1-3 帧
          const disappearFrames = Math.floor(Math.random() * 3) + 1
          for (let j = 0; j < disappearFrames && i + j < totalFrames; j++) {
            path.push(null)
          }
          i += disappearFrames
        }
      }

      return path
    },

    getDirection (prevPoint, currentPoint) {
      if (!prevPoint || !currentPoint) return '静止'

      const dx = currentPoint.x - prevPoint.x
      const dy = currentPoint.y - prevPoint.y

      if (Math.abs(dx) < 0.1 && Math.abs(dy) < 0.1) return '静止'

      // 计算移动方向
      const angle = Math.atan2(dy, dx) * 180 / Math.PI

      if (angle > -22.5 && angle <= 22.5) return '向右'
      if (angle > 22.5 && angle <= 67.5) return '右下'
      if (angle > 67.5 && angle <= 112.5) return '向下'
      if (angle > 112.5 && angle <= 157.5) return '左下'
      if (angle > 157.5 || angle <= -157.5) return '向左'
      if (angle > -157.5 && angle <= -112.5) return '左上'
      if (angle > -112.5 && angle <= -67.5) return '向上'
      if (angle > -67.5 && angle <= -22.5) return '右上'

      return '静止'
    }
  }
}
</script>

<style scoped>
.video-tracking-container {
  position: relative;
  width: 100%;
  margin: 0 auto;
  max-width: 960px;
}

.video-wrapper {
  position: relative;
  width: 100%;
  overflow: hidden;
  background-color: #000;
  aspect-ratio: 16/9;
}

.main-video {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.tracking-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.tracking-box {
  position: absolute;
  border: 2px solid;
  border-radius: 2px;
  box-sizing: border-box;
}

.tracking-label {
  position: absolute;
  top: -22px;
  left: 0;
  padding: 2px 6px;
  font-size: 12px;
  background-color: rgba(230, 162, 60, 0.8);
  color: #fff;
  border-radius: 2px;
  white-space: nowrap;
}

.target-label {
  background-color: rgba(103, 194, 58, 0.8);
}

.trajectory-svg {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.controls-wrapper {
  margin-top: 12px;
  padding: 10px;
  display: flex;
  align-items: center;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.info-panel {
  margin-top: 16px;
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  border-left: 4px solid #67C23A;
}

.info-panel h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: #333;
}

.info-panel p {
  margin: 0;
  line-height: 1.5;
}
</style>
