<template>
  <div class="user-management-container">
    <div class="page-header">
      <div class="header-left">
        <el-button icon="el-icon-back" @click="goBack">返回</el-button>
        <h2>用户管理</h2>
      </div>
      <div class="header-actions">
        <el-input
          placeholder="搜索用户名/姓名/邮箱"
          v-model="searchKeyword"
          clearable
          @clear="fetchUsers"
          prefix-icon="el-icon-search"
          style="width: 250px;"
        >
          <el-button slot="append" icon="el-icon-search" @click="fetchUsers"></el-button>
        </el-input>
        <el-button type="primary" @click="showAddUserDialog">添加用户</el-button>
        <el-button
          type="danger"
          :disabled="selectedUsers.length === 0"
          @click="batchDeleteUsers"
        >批量删除</el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-table
      :data="users"
      border
      style="width: 100%"
      @selection-change="handleSelectionChange"
      v-loading="loading"
    >
      <el-table-column type="selection" width="55"></el-table-column>
      <el-table-column prop="username" label="用户名" width="120"></el-table-column>
      <el-table-column prop="real_name" label="姓名" width="120"></el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template slot-scope="scope">
          <el-tag :type="scope.row.role === 'admin' ? 'danger' : 'success'">
            {{ scope.row.role === 'admin' ? '管理员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="email" label="邮箱" width="200"></el-table-column>
      <el-table-column prop="phone" label="电话" width="150"></el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="180"></el-table-column>
      <el-table-column prop="updated_at" label="更新时间" width="180"></el-table-column>
      <el-table-column label="操作" width="180">
        <template slot-scope="scope">
          <el-button
            size="mini"
            @click="editUser(scope.row)"
          >编辑</el-button>
          <el-button
            size="mini"
            type="danger"
            @click="deleteUser(scope.row)"
            :disabled="scope.row.user_id === currentUserId"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-container">
      <el-pagination
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
        :current-page="pagination.page"
        :page-sizes="[10, 20, 50, 100]"
        :page-size="pagination.pageSize"
        layout="total, sizes, prev, pager, next, jumper"
        :total="pagination.total"
      >
      </el-pagination>
    </div>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog :title="dialogTitle" :visible.sync="dialogVisible" width="500px">
      <el-form :model="userForm" :rules="userRules" ref="userForm" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" :disabled="dialogMode === 'edit'"></el-input>
        </el-form-item>
        <el-form-item label="姓名" prop="realName">
          <el-input v-model="userForm.realName"></el-input>
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="请选择角色">
            <el-option label="管理员" value="admin"></el-option>
            <el-option label="普通用户" value="user"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-if="dialogMode === 'add'">
          <el-input v-model="userForm.password" type="password" show-password></el-input>
        </el-form-item>
        <el-form-item label="密码" prop="password" v-else>
          <el-input v-model="userForm.password" type="password" show-password placeholder="留空表示不修改密码"></el-input>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email"></el-input>
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="userForm.phone"></el-input>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="submitUserForm" :loading="submitting">确 定</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'UserManagement',
  data () {
    return {
      users: [],
      loading: false,
      submitting: false,
      selectedUsers: [],
      searchKeyword: '',
      currentUserId: null,
      pagination: {
        page: 1,
        pageSize: 10,
        total: 0
      },
      dialogVisible: false,
      dialogMode: 'add', // 'add' 或 'edit'
      dialogTitle: '添加用户',
      userForm: {
        userId: '',
        username: '',
        password: '',
        realName: '',
        email: '',
        phone: '',
        role: 'user'
      },
      userRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur', validator: this.validatePassword }
        ],
        email: [
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ],
        role: [
          { required: true, message: '请选择角色', trigger: 'change' }
        ]
      }
    }
  },
  created () {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    if (!user.role || user.role !== 'admin') {
      this.$message.error('您没有权限访问此页面')
      this.$router.push('/')
    }
    this.getCurrentUser()
    this.fetchUsers()
  },
  methods: {
    // 返回上一页
    goBack () {
      this.$router.go(-1) // 返回上一页
    },
    // 获取当前登录用户信息
    getCurrentUser () {
      const user = JSON.parse(localStorage.getItem('user') || '{}')
      this.currentUserId = user.user_id
    },

    // 获取用户列表
    fetchUsers () {
      this.loading = true
      const params = {
        page: this.pagination.page,
        pageSize: this.pagination.pageSize
      }

      if (this.searchKeyword) {
        params.keyword = this.searchKeyword
      }

      axios.get('/api/users', { params })
        .then(response => {
          if (response.data.success) {
            this.users = response.data.data
            this.pagination.total = response.data.total
          } else {
            this.$message.error(response.data.message || '获取用户列表失败')
          }
        })
        .catch(error => {
          this.$message.error('获取用户列表失败: ' + (error.response && error.response.data && error.response.data.message ? error.response.data.message : error.message))
        })
        .finally(() => {
          this.loading = false
        })
    },

    // 处理分页大小变化
    handleSizeChange (val) {
      this.pagination.pageSize = val
      this.fetchUsers()
    },

    // 处理页码变化
    handleCurrentChange (val) {
      this.pagination.page = val
      this.fetchUsers()
    },

    // 处理表格选择变化
    handleSelectionChange (val) {
      this.selectedUsers = val
    },

    // 显示添加用户对话框
    showAddUserDialog () {
      this.dialogMode = 'add'
      this.dialogTitle = '添加用户'
      this.resetUserForm()
      this.dialogVisible = true
    },

    // 编辑用户
    editUser (user) {
      this.dialogMode = 'edit'
      this.dialogTitle = '编辑用户'
      this.resetUserForm()

      // 填充表单
      this.userForm.userId = user.user_id
      this.userForm.username = user.username
      this.userForm.realName = user.real_name
      this.userForm.email = user.email
      this.userForm.phone = user.phone
      this.userForm.role = user.role
      this.userForm.password = '' // 编辑时默认密码为空

      this.dialogVisible = true
    },

    // 重置用户表单
    resetUserForm () {
      if (this.$refs.userForm) {
        this.$refs.userForm.resetFields()
      }

      this.userForm = {
        userId: '',
        username: '',
        password: '',
        realName: '',
        email: '',
        phone: '',
        role: 'user'
      }
    },

    // 验证密码
    validatePassword (rule, value, callback) {
      if (this.dialogMode === 'add' && (!value || value.length < 6)) {
        callback(new Error('密码不能少于6个字符'))
      } else if (this.dialogMode === 'edit' && value && value.length < 6) {
        callback(new Error('如果修改密码，不能少于6个字符'))
      } else {
        callback()
      }
    },

    // 提交用户表单
    submitUserForm () {
      this.$refs.userForm.validate((valid) => {
        if (valid) {
          this.submitting = true

          // 构建请求数据
          const userData = {
            username: this.userForm.username,
            password: this.userForm.password,
            role: this.userForm.role,
            realName: this.userForm.realName,
            email: this.userForm.email,
            phone: this.userForm.phone
          }

          // 如果编辑模式且密码为空，则不更新密码
          if (this.dialogMode === 'edit' && !this.userForm.password) {
            delete userData.password
          }

          if (this.dialogMode === 'add') {
            // 添加用户
            axios.post('/api/users', userData)
              .then(response => {
                if (response.data.success) {
                  this.$message.success('用户添加成功')
                  this.dialogVisible = false
                  this.fetchUsers()
                } else {
                  this.$message.error(response.data.message || '添加用户失败')
                }
              })
              .catch(error => {
                this.$message.error('添加用户失败: ' + (error.response && error.response.data && error.response.data.message ? error.response.data.message : error.message))
              })
              .finally(() => {
                this.submitting = false
              })
          } else {
            // 更新用户
            axios.put(`/api/users/${this.userForm.userId}`, userData)
              .then(response => {
                if (response.data.success) {
                  this.$message.success('用户更新成功')
                  this.dialogVisible = false
                  this.fetchUsers()
                } else {
                  this.$message.error(response.data.message || '更新用户失败')
                }
              })
              .catch(error => {
                this.$message.error('更新用户失败: ' + (error.response && error.response.data && error.response.data.message ? error.response.data.message : error.message))
              })
              .finally(() => {
                this.submitting = false
              })
          }
        } else {
          return false
        }
      })
    },

    // 删除单个用户
    deleteUser (user) {
      this.$confirm(`确定要删除用户 "${user.username}" 吗?`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        axios.delete(`/api/users/${user.user_id}`)
          .then(response => {
            if (response.data.success) {
              this.$message.success('用户删除成功')
              this.fetchUsers()
            } else {
              this.$message.error(response.data.message || '删除用户失败')
            }
          })
          .catch(error => {
            this.$message.error('删除用户失败: ' + (error.response && error.response.data && error.response.data.message ? error.response.data.message : error.message))
          })
      }).catch(() => {
        // 取消删除，不做任何操作
      })
    },

    // 批量删除用户
    batchDeleteUsers () {
      if (this.selectedUsers.length === 0) {
        this.$message.warning('请选择要删除的用户')
        return
      }

      // 检查是否包含当前用户
      const includesSelf = this.selectedUsers.some(user => user.user_id === this.currentUserId)
      if (includesSelf) {
        this.$message.warning('不能删除当前登录的用户账户')
        return
      }

      this.$confirm(`确定要删除选中的 ${this.selectedUsers.length} 个用户吗?`, '警告', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const ids = this.selectedUsers.map(user => user.user_id)

        axios.post('/api/users/batch-delete', { ids })
          .then(response => {
            if (response.data.success) {
              this.$message.success(`成功删除 ${response.data.count} 个用户`)
              this.fetchUsers()
            } else {
              this.$message.error(response.data.message || '批量删除用户失败')
            }
          })
          .catch(error => {
            this.$message.error('批量删除用户失败: ' + (error.response && error.response.data && error.response.data.message ? error.response.data.message : error.message))
          })
      }).catch(() => {
        // 取消删除，不做任何操作
      })
    }
  }
}
</script>

<style scoped>
.user-management-container {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.header-left h2 {
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>
