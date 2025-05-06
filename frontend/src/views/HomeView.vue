<template>
  <div class="container">
    <Menu></Menu>
    <div class="title">
      <p>基于深度学习的校园学生轨迹追踪系统设计与实现</p>
    </div>
    <div class="button">
      <el-button type="info" round @click="showLoginDialog">
        <span>登录/注册</span>
      </el-button>
    </div>

    <!-- 登录对话框 -->
    <el-dialog title="登录" :visible.sync="loginDialogVisible" width="400px" center>
      <div class="login-box">
        <div class="login-logo">
          <img src="../assets/hfut.png" alt="logo"/>
          <h2>校园监控追踪系统</h2>
        </div>
        <el-form :model="loginForm" :rules="loginRules" ref="loginForm">
          <el-form-item prop="username">
            <el-input prefix-icon="el-icon-user" v-model="loginForm.username" placeholder="用户名"></el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input prefix-icon="el-icon-lock" v-model="loginForm.password" type="password" placeholder="密码"></el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" class="login-btn" @click="handleLogin" :loading="loading">登录</el-button>
          </el-form-item>
          <div class="login-options">
            <span @click="switchToRegister">没有账号？立即注册</span>
          </div>
        </el-form>
      </div>
    </el-dialog>

    <!-- 注册对话框 -->
    <el-dialog title="注册" :visible.sync="registerDialogVisible" width="400px" center>
      <div class="register-box">
        <div class="register-logo">
          <img src="../assets/hfut.png" alt="logo"/>
          <h2>注册新账号</h2>
        </div>
        <el-form :model="registerForm" :rules="registerRules" ref="registerForm">
          <el-form-item prop="username">
            <el-input prefix-icon="el-icon-user" v-model="registerForm.username" placeholder="用户名"></el-input>
          </el-form-item>
          <el-form-item prop="password">
            <el-input prefix-icon="el-icon-lock" v-model="registerForm.password" type="password" placeholder="密码"></el-input>
          </el-form-item>
          <el-form-item prop="confirmPassword">
            <el-input prefix-icon="el-icon-lock" v-model="registerForm.confirmPassword" type="password" placeholder="确认密码"></el-input>
          </el-form-item>
          <el-form-item prop="realName">
            <el-input prefix-icon="el-icon-user" v-model="registerForm.realName" placeholder="真实姓名"></el-input>
          </el-form-item>
          <el-form-item prop="email">
            <el-input prefix-icon="el-icon-message" v-model="registerForm.email" placeholder="电子邮箱"></el-input>
          </el-form-item>
          <el-form-item prop="phone">
            <el-input prefix-icon="el-icon-phone" v-model="registerForm.phone" placeholder="联系电话"></el-input>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" class="register-btn" @click="handleRegister" :loading="loading">注册</el-button>
          </el-form-item>
          <div class="register-options">
            <span @click="switchToLogin">已有账号？返回登录</span>
          </div>
        </el-form>
      </div>
    </el-dialog>
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'
import axios from 'axios'

export default {
  name: 'Home',
  components: {
    Menu
  },
  data () {
    const validatePass2 = (rule, value, callback) => {
      if (value !== this.registerForm.password) {
        callback(new Error('两次输入密码不一致!'))
      } else {
        callback()
      }
    }
    return {
      loginDialogVisible: false,
      registerDialogVisible: false,
      loading: false,
      loginForm: {
        username: '',
        password: ''
      },
      loginRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' }
        ]
      },
      registerForm: {
        username: '',
        password: '',
        confirmPassword: '',
        realName: '',
        email: '',
        phone: ''
      },
      registerRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能小于6个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请再次输入密码', trigger: 'blur' },
          { validator: validatePass2, trigger: 'blur' }
        ],
        email: [
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ]
      }
    }
  },
  methods: {
    showLoginDialog () {
      this.loginDialogVisible = true
    },
    switchToRegister () {
      this.loginDialogVisible = false
      this.registerDialogVisible = true
    },
    switchToLogin () {
      this.registerDialogVisible = false
      this.loginDialogVisible = true
    },
    handleLogin () {
      this.$refs.loginForm.validate(valid => {
        if (valid) {
          this.loading = true
          axios.post('/api/auth/login', this.loginForm)
            .then(response => {
              this.loading = false
              if (response.data.success) {
                // 保存令牌到本地存储
                localStorage.setItem('token', response.data.token)
                localStorage.setItem('user', JSON.stringify(response.data.user))
                this.$message.success('登录成功')
                this.loginDialogVisible = false
                this.$router.push('/Function')
              } else {
                this.$message.error(response.data.message || '登录失败')
              }
            })
            .catch(error => {
              this.loading = false
              this.$message.error(`登录失败：${(error.response && error.response.data && error.response.data.message) || '服务器错误'}`)
            })
        }
      })
    },
    handleRegister () {
      this.$refs.registerForm.validate(valid => {
        if (valid) {
          this.loading = true
          const formData = { ...this.registerForm }
          delete formData.confirmPassword // 不需要发送确认密码

          axios.post('/api/auth/register', formData)
            .then(response => {
              this.loading = false
              if (response.data.success) {
                this.$message.success('注册成功，请登录')
                this.registerDialogVisible = false
                this.loginDialogVisible = true
              } else {
                this.$message.error(response.data.message || '注册失败')
              }
            })
            .catch(error => {
              this.loading = false
              this.$message.error(`注册失败：${(error.response && error.response.data && error.response.data.message) || '服务器错误'}`)
            })
        }
      })
    }
  }
}
</script>

<style scoped>
.container {
  background: url("../assets/home_page.jpg") no-repeat center;
  background-size: 100% 100%;
}

.container::after {
  z-index: -1;
  position: absolute;
  content: '';
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgb(9, 9, 9);
  opacity: 0.3;
}

.logo {
  margin-left: 3%;
  padding-top: 3%;
  width: 8%;
}

.logo img {
  width: 100%;
  z-index: 2;
}

.title {
  margin-top: 7%;
  font-size: 4vw;
  color: #ffffff;
}

.title span {
  letter-spacing: 2vw;
}

.content {
  margin-top: 3%;
  color: #ffffff;
  font-size: 3vw;
}

.button {
  margin-top: 2%;
}

.button span {
  letter-spacing: 0.8vw;
}

.button button {
  width: 20%;
  font-size: 2vw;
  border: 1px solid white;
  border-radius: 8px;
  color: white;
  background: none;
  height: 70px;
  width: 230px;
}

.button button:hover {
  border: none;
  background-color: rgba(255, 255, 255, 0.763);
  color: #4d86ff;
}

/* 登录和注册样式 */
.login-box, .register-box {
  width: 100%;
}

.login-logo, .register-logo {
  text-align: center;
  margin-bottom: 20px;
}

.login-logo img, .register-logo img {
  width: 60px;
  margin-bottom: 10px;
}

.login-btn, .register-btn {
  width: 100%;
  margin-top: 10px;
}

.login-options, .register-options {
  text-align: right;
  margin-top: 15px;
  font-size: 14px;
  color: #409EFF;
  cursor: pointer;
}

/* 对话框样式优化 */
::v-deep(.el-dialog) {
  background-color: rgba(255, 255, 255, 0.95);
  border-radius: 10px;
}

::v-deep(.el-dialog__title) {
  font-weight: bold;
}
</style>
