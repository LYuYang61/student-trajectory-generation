<template>
  <div class="profile-container">
    <el-card class="profile-card">
      <div slot="header" class="profile-header">
        <span>个人信息</span>
        <div>
          <el-button @click="goBack" type="info" plain icon="el-icon-back">返回</el-button>
          <el-button v-if="!isEditing" type="primary" @click="enableEdit">编辑</el-button>
        </div>
      </div>

      <el-form ref="profileForm" :model="userForm" :rules="rules" label-width="100px" :disabled="!isEditing">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" disabled></el-input>
        </el-form-item>

        <el-form-item label="真实姓名" prop="realName">
          <el-input v-model="userForm.realName"></el-input>
        </el-form-item>

        <el-form-item label="电子邮箱" prop="email">
          <el-input v-model="userForm.email"></el-input>
        </el-form-item>

        <el-form-item label="联系电话" prop="phone">
          <el-input v-model="userForm.phone"></el-input>
        </el-form-item>

        <el-form-item v-if="isEditing">
          <el-button type="primary" @click="updateProfile" :loading="loading">保存修改</el-button>
          <el-button @click="cancelEdit">取消</el-button>
        </el-form-item>

        <el-form-item label="修改密码" v-if="isEditing">
          <el-button type="warning" @click="showPasswordDialog">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 修改密码弹窗 -->
    <el-dialog title="修改密码" :visible.sync="passwordDialogVisible" width="550px">
      <el-form ref="passwordForm" :model="passwordForm" :rules="passwordRules" label-width="120px">
        <el-form-item label="原密码" prop="oldPassword">
          <el-input v-model="passwordForm.oldPassword" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" show-password></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="changePassword" :loading="pwdLoading">确认修改</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'ProfileView',
  data () {
    const validateConfirmPassword = (rule, value, callback) => {
      if (value !== this.passwordForm.newPassword) {
        callback(new Error('两次输入密码不一致!'))
      } else {
        callback()
      }
    }

    return {
      userForm: {
        username: '',
        realName: '',
        email: '',
        phone: ''
      },
      originalUserForm: {}, // 保存原始数据，用于取消编辑
      isEditing: false,
      loading: false,
      pwdLoading: false,
      passwordDialogVisible: false,
      passwordForm: {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      rules: {
        email: [
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ],
        phone: [
          { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
        ]
      },
      passwordRules: {
        oldPassword: [
          { required: true, message: '请输入原密码', trigger: 'blur' }
        ],
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
          { min: 6, message: '密码长度不能小于6位', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认新密码', trigger: 'blur' },
          { validator: validateConfirmPassword, trigger: 'blur' }
        ]
      }
    }
  },
  created () {
    this.fetchUserProfile()
  },
  methods: {
    goBack () {
      this.$router.go(-1) // 返回上一页
    },
    fetchUserProfile () {
      const token = localStorage.getItem('token')
      if (!token) {
        this.$message.error('您尚未登录，请先登录')
        this.$router.push('/home')
        return
      }

      axios.get('/api/user/profile', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      })
        .then(response => {
          if (response.data.success) {
            this.userForm = response.data.user
            this.originalUserForm = { ...response.data.user }
          } else {
            this.$message.error(response.data.message || '获取用户信息失败')
          }
        })
        .catch(error => {
          this.$message.error(`获取用户信息失败：${(error.response && error.response.data && error.response.data.message) || '服务器错误'}`)
          if (error.response && error.response.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            this.$router.push('/home')
          }
        })
    },

    enableEdit () {
      this.isEditing = true
    },

    cancelEdit () {
      this.userForm = { ...this.originalUserForm }
      this.isEditing = false
    },

    updateProfile () {
      this.$refs.profileForm.validate(valid => {
        if (valid) {
          this.loading = true
          const token = localStorage.getItem('token')

          axios.put('/api/user/profile', this.userForm, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          })
            .then(response => {
              this.loading = false
              if (response.data.success) {
                this.$message.success(response.data.message || '个人信息更新成功')
                this.originalUserForm = { ...this.userForm }
                this.isEditing = false
              } else {
                this.$message.error(response.data.message || '更新失败')
              }
            })
            .catch(error => {
              this.loading = false
              this.$message.error(`更新失败：${(error.response && error.response.data && error.response.data.message) || '服务器错误'}`)
            })
        }
      })
    },

    showPasswordDialog () {
      this.passwordForm = {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
      this.passwordDialogVisible = true
    },

    changePassword () {
      this.$refs.passwordForm.validate(valid => {
        if (valid) {
          this.pwdLoading = true
          const token = localStorage.getItem('token')

          axios.put('/api/user/change-password', this.passwordForm, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          })
            .then(response => {
              this.pwdLoading = false
              if (response.data.success) {
                this.$message.success(response.data.message || '密码修改成功')
                this.passwordDialogVisible = false
              } else {
                this.$message.error(response.data.message || '密码修改失败')
              }
            })
            .catch(error => {
              this.pwdLoading = false
              this.$message.error(`密码修改失败：${(error.response && error.response.data && error.response.data.message) || '服务器错误'}`)
            })
        }
      })
    }
  }
}
</script>

<style scoped>
.profile-container {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.profile-card {
  margin-bottom: 20px;
}

.profile-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.profile-header h2 {
  margin: 0;
}

.profile-header .el-button {
  margin-left: 10px;
}
</style>
