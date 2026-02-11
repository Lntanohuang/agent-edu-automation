<template>
  <div class="intelligent-grading">
    <!-- 顶部操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <h2>智能报告批阅</h2>
        <p>AI 辅助批量批阅学生作业，提供详细反馈和评分建议</p>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">新建批阅任务</el-button>
        <el-button :icon="Upload">批量导入</el-button>
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="stat in statistics" :key="stat.title">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <el-icon size="40" :color="stat.color"><component :is="stat.icon" /></el-icon>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 任务列表 -->
    <el-card class="task-list-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <div class="header-tabs">
            <el-radio-group v-model="activeTab" size="large">
              <el-radio-button label="all">全部任务</el-radio-button>
              <el-radio-button label="pending">进行中</el-radio-button>
              <el-radio-button label="completed">已完成</el-radio-button>
            </el-radio-group>
          </div>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索任务..."
            style="width: 300px"
            clearable
            :prefix-icon="Search"
          />
        </div>
      </template>
      
      <el-table :data="filteredTasks" style="width: 100%" v-loading="loading">
        <el-table-column type="index" width="50" />
        <el-table-column prop="title" label="任务名称" min-width="180">
          <template #default="{ row }">
            <div class="task-name">
              <el-icon size="18" color="#409eff"><Document /></el-icon>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="subject" label="学科" width="100" />
        <el-table-column prop="type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.type)">{{ getTypeText(row.type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="submissions.length" label="提交数" width="100">
          <template #default="{ row }">
            <span>{{ row.submissions.length }} 份</span>
          </template>
        </el-table-column>
        <el-table-column prop="gradedCount" label="已批阅" width="100">
          <template #default="{ row }">
            <span>{{ getGradedCount(row) }} 份</span>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="getProgress(row)"
              :status="getProgressStatus(row)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="viewTask(row)">查看</el-button>
            <el-button type="success" text size="small" @click="startGrading(row)" :disabled="row.status === 'completed'">开始批阅</el-button>
            <el-button type="danger" text size="small" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          background
          layout="prev, pager, next, jumper, ->, total"
          :total="100"
          :page-size="10"
        />
      </div>
    </el-card>
    
    <!-- 新建任务对话框 -->
    <el-dialog
      v-model="showCreateDialog"
      title="新建批阅任务"
      width="700px"
      destroy-on-close
    >
      <el-form :model="taskForm" label-position="top" :rules="taskRules" ref="taskFormRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务名称" prop="title">
              <el-input v-model="taskForm.title" placeholder="如：高一期中作文批阅" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学科" prop="subject">
              <el-select v-model="taskForm.subject" placeholder="选择学科" style="width: 100%">
                <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="年级" prop="grade">
              <el-select v-model="taskForm.grade" placeholder="选择年级" style="width: 100%">
                <el-option v-for="g in grades" :key="g" :label="g" :value="g" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="作业类型" prop="type">
              <el-select v-model="taskForm.type" placeholder="选择类型" style="width: 100%">
                <el-option label="作文" value="essay" />
                <el-option label="代码" value="code" />
                <el-option label="数学解答" value="math" />
                <el-option label="英语作文" value="english" />
                <el-option label="其他" value="other" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="评分标准">
          <div class="rubric-list">
            <div
              v-for="(item, index) in taskForm.rubric"
              :key="index"
              class="rubric-item"
            >
              <el-input v-model="item.criteria" placeholder="评分项" style="width: 200px" />
              <el-slider v-model="item.weight" :min="0" :max="100" style="flex: 1" />
              <span class="weight-value">{{ item.weight }}%</span>
              <el-button type="danger" :icon="Delete" circle size="small" @click="removeRubricItem(index)" />
            </div>
            <el-button type="primary" :icon="Plus" @click="addRubricItem">添加评分项</el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="上传学生作业">
          <el-upload
            drag
            action="/api/upload"
            multiple
            :auto-upload="false"
            :on-change="handleFileChange"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 docx, pdf, txt, zip 格式，单个文件不超过 10MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createTask" :loading="creating">创建任务</el-button>
      </template>
    </el-dialog>
    
    <!-- 批阅详情抽屉 -->
    <el-drawer
      v-model="showDetailDrawer"
      :title="currentTask?.title"
      size="70%"
      destroy-on-close
    >
      <div class="grading-detail">
        <!-- 任务概览 -->
        <el-card class="overview-card" shadow="never">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="overview-item">
                <div class="overview-label">总提交数</div>
                <div class="overview-value">{{ currentTask?.submissions.length || 0 }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="overview-item">
                <div class="overview-label">已批阅</div>
                <div class="overview-value">{{ currentTask ? getGradedCount(currentTask) : 0 }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="overview-item">
                <div class="overview-label">平均分</div>
                <div class="overview-value">{{ currentTask ? getAverageScore(currentTask) : '-' }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="overview-item">
                <div class="overview-label">状态</div>
                <div class="overview-value">
                  <el-tag :type="getStatusType(currentTask?.status)">
                    {{ getStatusText(currentTask?.status) }}
                  </el-tag>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>
        
        <!-- 操作栏 -->
        <div class="detail-actions">
          <el-button type="primary" :icon="VideoPlay" @click="batchGrading" :loading="grading">
            {{ grading ? '批阅中...' : '开始AI批阅' }}
          </el-button>
          <el-button :icon="Download" @click="exportResults">导出结果</el-button>
          <el-button :icon="View" @click="showRubric = true">查看评分标准</el-button>
        </div>
        
        <!-- 学生作业列表 -->
        <el-card shadow="never">
          <el-table :data="currentTask?.submissions" style="width: 100%">
            <el-table-column prop="studentName" label="学生姓名" width="120" />
            <el-table-column prop="studentId" label="学号" width="120" />
            <el-table-column label="内容预览" min-width="200">
              <template #default="{ row }">
                <el-text line-clamp="2">{{ row.content }}</el-text>
              </template>
            </el-table-column>
            <el-table-column prop="score" label="得分" width="100">
              <template #default="{ row }">
                <span :class="getScoreClass(row.feedback?.overallScore)">
                  {{ row.feedback?.overallScore ?? '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="gradedAt" label="批阅时间" width="150">
              <template #default="{ row }">
                {{ row.gradedAt ? formatDate(row.gradedAt) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" text size="small" @click="viewSubmission(row)">查看详情</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
    </el-drawer>
    
    <!-- 作业详情对话框 -->
    <el-dialog
      v-model="showSubmissionDialog"
      title="批阅详情"
      width="900px"
      destroy-on-close
    >
      <div v-if="currentSubmission" class="submission-detail">
        <el-row :gutter="24">
          <el-col :span="14">
            <h4>学生作业内容</h4>
            <div class="submission-content">
              {{ currentSubmission.content }}
            </div>
          </el-col>
          <el-col :span="10">
            <h4>AI 批阅结果</h4>
            <div v-if="currentSubmission.feedback" class="feedback-panel">
              <div class="score-display">
                <el-progress
                  type="dashboard"
                  :percentage="currentSubmission.feedback.overallScore"
                  :color="getScoreColor(currentSubmission.feedback.overallScore)"
                />
                <div class="score-label">总评分</div>
              </div>
              
              <div class="feedback-section">
                <h5>评语</h5>
                <p>{{ currentSubmission.feedback.overallComment }}</p>
              </div>
              
              <div class="feedback-section">
                <h5>优点</h5>
                <ul>
                  <li v-for="(strength, i) in currentSubmission.feedback.strengths" :key="i">
                    {{ strength }}
                  </li>
                </ul>
              </div>
              
              <div class="feedback-section">
                <h5>改进建议</h5>
                <ul>
                  <li v-for="(suggestion, i) in currentSubmission.feedback.suggestions" :key="i">
                    {{ suggestion }}
                  </li>
                </ul>
              </div>
              
              <div class="feedback-section">
                <h5>详细点评</h5>
                <p>{{ currentSubmission.feedback.detailedComments }}</p>
              </div>
            </div>
            <el-empty v-else description="暂未完成批阅" />
          </el-col>
        </el-row>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive } from 'vue'
import { useGradingStore, type GradingTask, type Submission } from '../stores/grading'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Upload,
  Search,
  Document,
  Delete,
  UploadFilled,
  VideoPlay,
  Download,
  View
} from '@element-plus/icons-vue'

const gradingStore = useGradingStore()
const loading = ref(false)
const activeTab = ref('all')
const searchKeyword = ref('')
const showCreateDialog = ref(false)
const showDetailDrawer = ref(false)
const showSubmissionDialog = ref(false)
const creating = ref(false)
const grading = ref(false)
const showRubric = ref(false)

const taskFormRef = ref()
const taskForm = reactive({
  title: '',
  subject: '',
  grade: '',
  type: 'essay' as const,
  rubric: [
    { criteria: '内容完整性', weight: 30, description: '内容是否完整' },
    { criteria: '逻辑结构', weight: 25, description: '结构是否清晰' },
    { criteria: '语言表达', weight: 25, description: '表达是否流畅' },
    { criteria: '创新性', weight: 20, description: '是否有创新' }
  ]
})

const taskRules = {
  title: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  subject: [{ required: true, message: '请选择学科', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  type: [{ required: true, message: '请选择作业类型', trigger: 'change' }]
}

const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治']
const grades = ['初一', '初二', '初三', '高一', '高二', '高三']

const statistics = [
  { title: '总任务数', value: gradingStore.tasks.length, icon: 'Document', color: '#409EFF' },
  { title: '待批阅', value: 23, icon: 'Timer', color: '#E6A23C' },
  { title: '已完成', value: 156, icon: 'DocumentChecked', color: '#67C23A' },
  { title: '平均用时', value: '2.5h', icon: 'TrendCharts', color: '#F56C6C' }
]

const filteredTasks = computed(() => {
  let tasks = gradingStore.tasks
  
  if (activeTab.value === 'pending') {
    tasks = tasks.filter(t => t.status !== 'completed')
  } else if (activeTab.value === 'completed') {
    tasks = tasks.filter(t => t.status === 'completed')
  }
  
  if (searchKeyword.value) {
    tasks = tasks.filter(t => t.title.includes(searchKeyword.value))
  }
  
  // 添加模拟数据
  if (tasks.length === 0) {
    return getMockTasks()
  }
  
  return tasks
})

const currentTask = ref<GradingTask | null>(null)
const currentSubmission = ref<Submission | null>(null)

const getMockTasks = (): GradingTask[] => [
  {
    id: '1',
    title: '高一期中语文作文批阅',
    subject: '语文',
    grade: '高一',
    type: 'essay',
    rubric: [],
    submissions: Array(45).fill(null).map((_, i) => ({
      id: String(i),
      studentName: `学生${i + 1}`,
      studentId: `2024${String(i + 1).padStart(3, '0')}`,
      content: '这是一篇关于春天的作文...',
      submittedAt: Date.now()
    })),
    createdAt: Date.now(),
    status: 'completed'
  },
  {
    id: '2',
    title: '高二数学函数专题作业',
    subject: '数学',
    grade: '高二',
    type: 'math',
    rubric: [],
    submissions: Array(38).fill(null).map((_, i) => ({
      id: String(i),
      studentName: `学生${i + 1}`,
      studentId: `2023${String(i + 1).padStart(3, '0')}`,
      content: '函数f(x) = x² + 2x + 1...',
      submittedAt: Date.now()
    })),
    createdAt: Date.now(),
    status: 'processing'
  },
  {
    id: '3',
    title: '初一英语作文《My Family》',
    subject: '英语',
    grade: '初一',
    type: 'english',
    rubric: [],
    submissions: Array(42).fill(null).map((_, i) => ({
      id: String(i),
      studentName: `学生${i + 1}`,
      studentId: `2025${String(i + 1).padStart(3, '0')}`,
      content: 'My family is a warm family...',
      submittedAt: Date.now()
    })),
    createdAt: Date.now(),
    status: 'pending'
  }
]

const getGradedCount = (task: GradingTask) => {
  return task.submissions.filter(s => s.feedback).length
}

const getProgress = (task: GradingTask) => {
  if (task.submissions.length === 0) return 0
  return Math.round((getGradedCount(task) / task.submissions.length) * 100)
}

const getProgressStatus = (task: GradingTask) => {
  const progress = getProgress(task)
  if (progress === 100) return 'success'
  return ''
}

const getAverageScore = (task: GradingTask) => {
  const graded = task.submissions.filter(s => s.feedback)
  if (graded.length === 0) return '-'
  const total = graded.reduce((sum, s) => sum + (s.feedback?.overallScore || 0), 0)
  return (total / graded.length).toFixed(1)
}

const getTypeTag = (type: string) => {
  const map: Record<string, string> = {
    essay: 'primary',
    code: 'success',
    math: 'warning',
    english: 'info',
    other: ''
  }
  return map[type] || ''
}

const getTypeText = (type: string) => {
  const map: Record<string, string> = {
    essay: '作文',
    code: '代码',
    math: '数学',
    english: '英语',
    other: '其他'
  }
  return map[type] || type
}

const getStatusType = (status?: string) => {
  const map: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success'
  }
  return map[status || ''] || 'info'
}

const getStatusText = (status?: string) => {
  const map: Record<string, string> = {
    pending: '待开始',
    processing: '进行中',
    completed: '已完成'
  }
  return map[status || ''] || status
}

const getScoreClass = (score?: number) => {
  if (!score) return ''
  if (score >= 90) return 'score-excellent'
  if (score >= 80) return 'score-good'
  if (score >= 60) return 'score-pass'
  return 'score-fail'
}

const getScoreColor = (score: number) => {
  if (score >= 90) return '#67C23A'
  if (score >= 80) return '#409EFF'
  if (score >= 60) return '#E6A23C'
  return '#F56C6C'
}

const addRubricItem = () => {
  taskForm.rubric.push({ criteria: '', weight: 10, description: '' })
}

const removeRubricItem = (index: number) => {
  taskForm.rubric.splice(index, 1)
}

const handleFileChange = () => {
  // 文件上传处理
}

const createTask = async () => {
  const valid = await taskFormRef.value?.validate().catch(() => false)
  if (!valid) return
  
  creating.value = true
  setTimeout(() => {
    gradingStore.createTask(taskForm)
    showCreateDialog.value = false
    creating.value = false
    ElMessage.success('任务创建成功！')
  }, 500)
}

const viewTask = (task: GradingTask) => {
  currentTask.value = task
  showDetailDrawer.value = true
}

const startGrading = (task: GradingTask) => {
  currentTask.value = task
  showDetailDrawer.value = true
}

const deleteTask = (task: GradingTask) => {
  ElMessageBox.confirm('确定删除该任务吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    gradingStore.deleteTask(task.id)
    ElMessage.success('删除成功')
  })
}

const batchGrading = async () => {
  if (!currentTask.value) return
  
  grading.value = true
  
  // 模拟 AI 批阅
  for (const submission of currentTask.value.submissions) {
    if (!submission.feedback) {
      await new Promise(resolve => setTimeout(resolve, 300))
      submission.feedback = {
        overallScore: Math.floor(Math.random() * 40) + 60,
        overallComment: '整体表现良好，有进步空间',
        strengths: ['思路清晰', '结构完整', '表达流畅'],
        weaknesses: ['细节不够完善', '举例不够丰富'],
        suggestions: ['多阅读范文', '加强练习', '注意细节'],
        criteriaScores: taskForm.rubric.map(r => ({
          criteriaId: r.criteria,
          score: Math.floor(Math.random() * 20) + 80,
          comment: '符合要求'
        })),
        detailedComments: '这是一份不错的作业，展现了学生对知识点的理解。建议在今后的学习中多关注细节，提高分析问题的深度。'
      }
      submission.gradedAt = Date.now()
    }
  }
  
  if (currentTask.value) {
    currentTask.value.status = 'completed'
  }
  
  grading.value = false
  ElMessage.success('批阅完成！')
}

const exportResults = () => {
  ElMessage.success('结果导出成功！')
}

const viewSubmission = (submission: Submission) => {
  currentSubmission.value = submission
  showSubmissionDialog.value = true
}

const formatDate = (timestamp: number) => {
  return new Date(timestamp).toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.intelligent-grading {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    
    .header-left {
      h2 {
        font-size: 24px;
        margin-bottom: 8px;
      }
      
      p {
        color: #666;
      }
    }
  }
  
  .stats-row {
    margin-bottom: 24px;
    
    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: 16px;
        
        .stat-info {
          .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #333;
          }
          
          .stat-title {
            font-size: 14px;
            color: #999;
          }
        }
      }
    }
  }
  
  .task-list-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .task-name {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    
    .pagination-wrapper {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
    }
  }
  
  .rubric-list {
    .rubric-item {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      
      .weight-value {
        min-width: 50px;
        text-align: right;
      }
    }
  }
  
  .grading-detail {
    .overview-card {
      margin-bottom: 20px;
      
      .overview-item {
        text-align: center;
        
        .overview-label {
          font-size: 14px;
          color: #666;
          margin-bottom: 8px;
        }
        
        .overview-value {
          font-size: 24px;
          font-weight: 700;
          color: #333;
        }
      }
    }
    
    .detail-actions {
      margin-bottom: 20px;
      display: flex;
      gap: 12px;
    }
  }
  
  .submission-detail {
    h4 {
      margin-bottom: 16px;
      padding-bottom: 12px;
      border-bottom: 1px solid #e4e7ed;
    }
    
    .submission-content {
      background: #f5f7fa;
      padding: 20px;
      border-radius: 8px;
      line-height: 1.8;
      min-height: 400px;
    }
    
    .feedback-panel {
      .score-display {
        text-align: center;
        margin-bottom: 24px;
        
        .score-label {
          margin-top: 8px;
          color: #666;
        }
      }
      
      .feedback-section {
        margin-bottom: 20px;
        
        h5 {
          font-size: 14px;
          color: #333;
          margin-bottom: 8px;
          font-weight: 600;
        }
        
        ul {
          padding-left: 20px;
          
          li {
            margin-bottom: 4px;
            color: #666;
          }
        }
        
        p {
          color: #666;
          line-height: 1.6;
        }
      }
    }
  }
  
  .score-excellent { color: #67C23A; font-weight: bold; }
  .score-good { color: #409EFF; font-weight: bold; }
  .score-pass { color: #E6A23C; }
  .score-fail { color: #F56C6C; }
}
</style>
