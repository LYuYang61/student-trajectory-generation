<template>
  <div class="container">
    <Menu></Menu>
    <div class="content">
      <div class="operation-bar">
        <el-button type="primary" size="small" @click="openAddDialog" v-if="isAdmin">添加学生</el-button>
        <el-button type="danger" size="small" @click="batchDelete" :disabled="selectedStudents.length === 0" v-if="isAdmin">批量删除</el-button>
        <el-upload
          class="excel-upload"
          action="#"
          :show-file-list="false"
          :on-change="handleExcelUpload"
          :auto-upload="false"
          accept=".xlsx,.xls"
          v-if="isAdmin">
          <el-button type="success" size="small">导入Excel</el-button>
        </el-upload>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索学生"
          class="search-input"
          clearable
          @clear="fetchStudents"
          @keyup.enter.native="searchStudents"
          size="small">
          <el-button slot="append" icon="el-icon-search" @click="searchStudents"></el-button>
        </el-input>
      </div>

      <el-table
        :data="students"
        border
        style="width: 100%"
        @selection-change="handleSelectionChange">
        <el-table-column
          type="selection"
          width="55">
        </el-table-column>
        <el-table-column
          prop="student_id"
          label="学号"
          width="120">
        </el-table-column>
        <el-table-column
          prop="name"
          label="姓名"
          width="100">
        </el-table-column>
        <el-table-column
          prop="gender"
          label="性别"
          width="80">
        </el-table-column>
        <el-table-column
          prop="grade"
          label="年级"
          width="100">
        </el-table-column>
        <el-table-column
          prop="major"
          label="专业"
          width="150">
        </el-table-column>
        <el-table-column
          prop="phone"
          label="电话"
          width="120">
        </el-table-column>
        <el-table-column
          prop="email"
          label="邮箱"
          width="180">
        </el-table-column>
        <el-table-column
          prop="birth_date"
          label="出生日期"
          width="120"
          :formatter="formatDate">
        </el-table-column>
        <el-table-column
          prop="enrollment_date"
          label="入学日期"
          width="120"
          :formatter="formatDate">
        </el-table-column>
        <el-table-column
          label="操作"
          width="250">
          <template slot-scope="scope">
            <template v-if="isAdmin">
              <el-button
                type="info"
                size="mini"
                @click="viewTrajectories(scope.row)"
                :disabled="!hasTrajectories(scope.row.student_id)"
              >查看轨迹</el-button>
              <el-button
                size="mini"
                @click="handleEdit(scope.row)">编辑</el-button>
              <el-button
                size="mini"
                type="danger"
                @click="handleDelete(scope.row)">删除</el-button>
            </template>
            <span v-else>仅可查看</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <div class="left-section">
          <span>共 {{ pagination.total }} 条</span>
          <el-select
            v-model="pagination.pageSize"
            placeholder="选择条数"
            @change="handleSizeChange"
            style="width: 100px"
          >
            <el-option v-for="size in pageSizes" :key="size" :label="`${size}条/页`" :value="size" />
          </el-select>
        </div>

        <div class="right-section">
          <el-pagination
            background
            layout="prev, pager, next, jumper"
            :total="pagination.total"
            :page-size="pagination.pageSize"
            :current-page="pagination.currentPage"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>
    </div>

    <!-- Add/Edit Student Dialog -->
    <el-dialog :title="dialogType === 'add' ? '添加学生' : '编辑学生'" :visible.sync="dialogVisible" width="50%">
      <el-form :model="studentForm" :rules="rules" ref="studentForm" label-width="100px">
        <el-form-item label="学号" prop="student_id">
          <el-input v-model="studentForm.student_id" :disabled="dialogType === 'edit'"></el-input>
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="studentForm.name"></el-input>
        </el-form-item>
        <el-form-item label="性别" prop="gender">
          <el-select v-model="studentForm.gender" placeholder="请选择性别">
            <el-option label="男" value="男"></el-option>
            <el-option label="女" value="女"></el-option>
            <el-option label="其他" value="其他"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="年级" prop="grade">
          <el-input v-model="studentForm.grade"></el-input>
        </el-form-item>
        <el-form-item label="专业" prop="major">
          <el-input v-model="studentForm.major"></el-input>
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="studentForm.phone"></el-input>
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="studentForm.email"></el-input>
        </el-form-item>
        <el-form-item label="出生日期" prop="birth_date">
          <el-date-picker v-model="studentForm.birth_date" type="date" placeholder="选择日期" value-format="yyyy-MM-dd"></el-date-picker>
        </el-form-item>
        <el-form-item label="入学日期" prop="enrollment_date">
          <el-date-picker v-model="studentForm.enrollment_date" type="date" placeholder="选择日期" value-format="yyyy-MM-dd"></el-date-picker>
        </el-form-item>
      </el-form>
      <div slot="footer" class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitForm">确定</el-button>
      </div>
    </el-dialog>

    <!-- Excel Preview Dialog -->
    <el-dialog title="Excel预览" :visible.sync="excelPreviewVisible" width="80%">
      <div class="excel-preview">
        <p>共导入 {{ excelData.length }} 条数据</p>
        <el-table :data="excelData.slice(0, 10)" border style="width: 100%">
          <el-table-column prop="student_id" label="学号" width="120"></el-table-column>
          <el-table-column prop="name" label="姓名" width="100"></el-table-column>
          <el-table-column prop="gender" label="性别" width="80"></el-table-column>
          <el-table-column prop="grade" label="年级" width="100"></el-table-column>
          <el-table-column prop="major" label="专业" width="150"></el-table-column>
          <el-table-column prop="phone" label="电话" width="120"></el-table-column>
          <el-table-column prop="email" label="邮箱" width="180"></el-table-column>
          <el-table-column prop="birth_date" label="出生日期" width="120"></el-table-column>
          <el-table-column prop="enrollment_date" label="入学日期" width="120"></el-table-column>
        </el-table>
        <p v-if="excelData.length > 10">仅显示前10条数据...</p>
      </div>
      <div slot="footer" class="dialog-footer">
        <el-button @click="excelPreviewVisible = false">取消</el-button>
        <el-button type="primary" @click="importExcelData">确认导入</el-button>
      </div>
    </el-dialog>

<!-- 轨迹信息对话框 -->
<el-dialog
  title="学生轨迹信息"
  :visible.sync="trajectoryDialogVisible"
  width="80%"
  :before-close="handleCloseTrajectoryDialog">

  <div v-if="studentTrajectories.length === 0" class="empty-data">
    暂无轨迹数据
  </div>

  <div v-else>
    <el-tabs v-model="activeTrajectoryTab">
      <el-tab-pane
        v-for="trajectory in studentTrajectories"
        :key="trajectory.id"
        :label="`轨迹 ${trajectory.id}`"
        :name="String(trajectory.id)">

        <el-descriptions title="轨迹基本信息" :column="1" border>
          <el-descriptions-item label="轨迹ID">{{ trajectory.id }}</el-descriptions-item>
          <el-descriptions-item label="开始时间">{{ trajectory.start_time }}</el-descriptions-item>
          <el-descriptions-item label="结束时间">{{ trajectory.end_time }}</el-descriptions-item>
          <el-descriptions-item label="摄像头序列">{{ trajectory.camera_sequence }}</el-descriptions-item>
          <el-descriptions-item label="总距离(米)">{{ trajectory.total_distance }}</el-descriptions-item>
          <el-descriptions-item label="平均速度(米/秒)">{{ trajectory.average_speed }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ trajectory.created_at }}</el-descriptions-item>
          <el-descriptions-item label="轨迹路径" :span="3">{{ formatTrajectoryPath(trajectory.path_points) }}
          </el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
    </el-tabs>
  </div>

  <span slot="footer" class="dialog-footer">
    <el-button @click="trajectoryDialogVisible = false">关闭</el-button>
  </span>
</el-dialog>
  </div>
</template>

<script>
import Menu from '../components/Menu.vue'
import * as XLSX from 'xlsx'
import {
  getStudents,
  addStudent,
  updateStudent,
  deleteStudent,
  batchDeleteStudents,
  importStudentsFromExcel,
  searchStudents
} from '../api/api'

export default {
  name: 'StudentManagement',
  components: { Menu },
  data () {
    return {
      isAdmin: false,
      pageSizes: [10, 20, 30, 40],
      students: [],
      trajectoryDialogVisible: false,
      studentTrajectories: [],
      activeTrajectoryTab: '0',
      studentTrajectoriesMap: {},
      selectedStudents: [],
      searchKeyword: '',
      pagination: {
        currentPage: 1,
        pageSize: 10,
        total: 0
      },
      dialogVisible: false,
      dialogType: 'add', // 'add' or 'edit'
      studentForm: {
        student_id: '',
        name: '',
        gender: '',
        grade: '',
        major: '',
        phone: '',
        email: '',
        birth_date: '',
        enrollment_date: ''
      },
      rules: {
        student_id: [
          { required: true, message: '请输入学号', trigger: 'blur' },
          { min: 3, max: 50, message: '长度在 3 到 50 个字符', trigger: 'blur' }
        ],
        name: [
          { required: true, message: '请输入姓名', trigger: 'blur' },
          { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
        ],
        gender: [
          { required: true, message: '请选择性别', trigger: 'change' }
        ],
        email: [
          { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
        ]
      },
      excelData: [],
      excelPreviewVisible: false,
      excelFile: null
    }
  },
  created () {
    this.fetchStudents()
    this.checkUserRole()
  },
  methods: {
    // 查看学生轨迹
    viewTrajectories (student) {
      this.loadStudentTrajectories(student.student_id)
    },

    // 加载学生轨迹数据
    async loadStudentTrajectories (studentId) {
      try {
        // 如果已经加载过该学生的轨迹，直接从缓存获取
        if (this.studentTrajectoriesMap[studentId]) {
          this.studentTrajectories = this.studentTrajectoriesMap[studentId]
          this.trajectoryDialogVisible = true
          return
        }

        this.$loading({ lock: true, text: '加载轨迹数据中...' })

        const response = await this.$http.get(`/students/${studentId}/trajectories`)

        console.log('获取轨迹数据:', response.data)

        if (response.data.success) {
          this.studentTrajectories = response.data.data
          this.studentTrajectoriesMap[studentId] = this.studentTrajectories

          if (this.studentTrajectories.length > 0) {
            this.activeTrajectoryTab = String(this.studentTrajectories[0].id)
          }
        } else {
          this.$message.error('获取轨迹数据失败')
        }

        console.log('轨迹数据:', this.studentTrajectories)

        this.trajectoryDialogVisible = true
      } catch (error) {
        console.error('获取轨迹数据失败:', error)
        this.$message.error('获取轨迹数据失败: ' + error.message)
      } finally {
        this.$loading().close()
      }
    },

    formatTrajectoryPath (pathPoints) {
      try {
        // 解析路径点JSON字符串
        let points
        if (typeof pathPoints === 'string') {
          points = JSON.parse(pathPoints)
        } else {
          points = pathPoints // 已经是对象时直接使用
        }

        if (!Array.isArray(points) || points.length === 0) {
          return '无路径点信息'
        }

        // 提取每个点的摄像头ID、名称和时间
        return points.map(point => {
          // 格式化时间为 HH:MM
          const time = point.timestamp ? new Date(point.timestamp).toLocaleString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
          }) : '未知时间'

          return `${point.camera_name || '摄像头' + point.camera_id}(${time})`
        }).join(' -> ')
      } catch (error) {
        console.error('解析路径点出错:', error)
        return '路径点格式无效'
      }
    },

    // 关闭轨迹对话框
    handleCloseTrajectoryDialog () {
      this.trajectoryDialogVisible = false
    },

    // 判断学生是否有轨迹记录
    hasTrajectories (studentId) {
      // 简单实现：所有学生都显示轨迹按钮
      // 实际应用中可以预先加载一个有轨迹记录的学生ID列表
      return true
    },

    checkUserRole () {
      const token = localStorage.getItem('token')
      if (!token) return

      try {
        const tokenParts = token.split('.')
        if (tokenParts.length !== 3) return

        const payload = JSON.parse(atob(tokenParts[1]))
        this.isAdmin = payload.role === 'admin'
      } catch (e) {
        console.error('解析token失败', e)
      }
    },
    formatDate (row, column, cellValue) {
      if (!cellValue) return ''

      // 处理日期格式
      const date = new Date(cellValue)
      if (isNaN(date.getTime())) return cellValue

      const year = date.getFullYear()
      const month = String(date.getMonth() + 1).padStart(2, '0')
      const day = String(date.getDate()).padStart(2, '0')

      return `${year}-${month}-${day}`
    },

    handleSizeChange (newSize) {
      this.pagination.pageSize = newSize
      this.pagination.currentPage = 1
      this.fetchStudents()
    },

    handleCurrentChange (page) {
      this.pagination.currentPage = page
      this.fetchStudents()
    },

    fetchStudents () {
      getStudents({
        page: this.pagination.currentPage,
        pageSize: this.pagination.pageSize
      }).then(res => {
        this.students = res.data.data
        this.pagination.total = res.data.total
        this.total = res.data.total // 同步更新total值，保持一致
      }).catch(err => {
        console.error(err)
        this.$message.error('获取学生列表失败')
      })
    },
    searchStudents () {
      if (!this.searchKeyword.trim()) {
        this.fetchStudents()
        return
      }

      searchStudents({
        keyword: this.searchKeyword,
        page: this.pagination.currentPage,
        pageSize: this.pagination.pageSize
      }).then(res => {
        this.students = res.data.data
        this.pagination.total = res.data.total
      }).catch(err => {
        console.error(err)
        this.$message.error('搜索学生失败')
      })
    },
    handleSelectionChange (val) {
      this.selectedStudents = val
    },
    resetForm () {
      this.studentForm = {
        student_id: '',
        name: '',
        gender: '',
        grade: '',
        major: '',
        phone: '',
        email: '',
        birth_date: '',
        enrollment_date: ''
      }
    },
    openAddDialog () {
      this.dialogType = 'add'
      this.resetForm()
      this.dialogVisible = true
    },
    handleEdit (row) {
      this.dialogType = 'edit'
      this.studentForm = { ...row }
      this.dialogVisible = true
    },
    submitForm () {
      this.$refs.studentForm.validate((valid) => {
        if (valid) {
          // 格式化日期字段
          const formData = { ...this.studentForm };

          // 确保日期格式正确
          ['birth_date', 'enrollment_date'].forEach(field => {
            if (formData[field]) {
              if (typeof formData[field] === 'string' && formData[field].includes('GMT')) {
                const date = new Date(formData[field])
                formData[field] = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
              }
            }
          })

          if (this.dialogType === 'add') {
            addStudent(formData).then(() => {
              this.$message.success('添加学生成功')
              this.dialogVisible = false
              this.fetchStudents()
            }).catch(err => {
              console.error(err)
              this.$message.error('添加学生失败')
            })
          } else {
            updateStudent(formData).then(() => {
              this.$message.success('更新学生信息成功')
              this.dialogVisible = false
              this.fetchStudents()
            }).catch(err => {
              console.error(err)
              this.$message.error('更新学生信息失败')
            })
          }
        } else {
          return false
        }
      })
    },
    handleDelete (row) {
      this.$confirm('确认删除该学生?', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        deleteStudent(row.student_id).then(() => {
          this.$message.success('删除学生成功')
          this.fetchStudents()
        }).catch(err => {
          console.error(err)
          this.$message.error('删除学生失败')
        })
      }).catch(() => {
        // 取消删除操作
      })
    },
    batchDelete () {
      if (this.selectedStudents.length === 0) {
        this.$message.warning('请先选择要删除的学生')
        return
      }

      this.$confirm(`确认删除选中的 ${this.selectedStudents.length} 名学生?`, '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(() => {
        const studentIds = this.selectedStudents.map(student => student.student_id)
        batchDeleteStudents({ ids: studentIds }).then(() => {
          this.$message.success('批量删除成功')
          this.fetchStudents()
        }).catch(err => {
          console.error(err)
          this.$message.error('批量删除失败')
        })
      }).catch(() => {
        // 取消删除操作
      })
    },
    handleExcelUpload (file) {
      if (file && (file.raw.type === 'application/vnd.ms-excel' ||
               file.raw.type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')) {
        this.excelFile = file.raw
        const reader = new FileReader()

        reader.onload = (e) => {
          const data = new Uint8Array(e.target.result)
          const workbook = XLSX.read(data, { type: 'array' })
          const firstSheetName = workbook.SheetNames[0]
          const worksheet = workbook.Sheets[firstSheetName]

          // 修改这行，添加dateNF参数保留原始日期格式
          let jsonData = XLSX.utils.sheet_to_json(worksheet, {
            raw: false,
            dateNF: 'yyyy-mm-dd'
          })

          // 处理数据格式，对日期字段进行额外处理
          this.excelData = jsonData.map(item => {
            // 格式化日期字段，确保格式为YYYY-MM-DD
            const formatDateField = (dateStr) => {
              if (!dateStr) return ''
              if (dateStr.includes('/')) {
                // 处理可能的9/10/21格式
                const parts = dateStr.split('/')
                if (parts.length === 3) {
                  let year = parts[2]
                  // 补全年份
                  if (year.length === 2) year = '20' + year
                  return `${year}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`
                }
              }
              return dateStr
            }

            return {
              student_id: item['学号'] || '',
              name: item['姓名'] || '',
              gender: item['性别'] || '',
              grade: item['年级'] || '',
              major: item['专业'] || '',
              phone: item['电话'] || '',
              email: item['邮箱'] || '',
              birth_date: formatDateField(item['出生日期']) || '',
              enrollment_date: formatDateField(item['入学日期']) || ''
            }
          })

          this.excelPreviewVisible = true
        }

        reader.readAsArrayBuffer(file.raw)
      } else {
        this.$message.error('请上传Excel格式文件')
      }
    },
    importExcelData () {
      if (this.excelData.length === 0) {
        this.$message.error('没有数据可导入')
        return
      }

      importStudentsFromExcel({ students: this.excelData }).then(() => {
        this.$message.success('导入成功')
        this.excelPreviewVisible = false
        this.fetchStudents()
      }).catch(err => {
        console.error(err)
        this.$message.error('导入失败')
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

.content {
  padding: 20px;
}

.operation-bar {
  margin-bottom: 20px;
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.operation-bar > * {
  margin-right: 15px;
}

.search-input {
  width: 250px;
  margin-left: auto;
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  padding: 10px 20px;
  background-color: #ccc;
}

.left-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.right-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.excel-preview {
  max-height: 500px;
  overflow-y: auto;
}

.excel-upload {
  display: inline-block;
}
</style>
