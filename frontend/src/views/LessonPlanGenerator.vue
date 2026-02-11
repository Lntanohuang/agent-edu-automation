<template>
  <div class="lesson-plan-generator">
    <el-row :gutter="24">
      <!-- 左侧：生成表单 -->
      <el-col :span="8">
        <el-card class="generate-form" shadow="hover">
          <template #header>
            <div class="card-header">
              <el-icon size="20" color="#67c23a"><Document /></el-icon>
              <span>教案生成参数</span>
            </div>
          </template>
          
          <el-form :model="form" label-position="top" :rules="rules" ref="formRef">
            <el-form-item label="学科" prop="subject">
              <el-select v-model="form.subject" placeholder="选择学科" style="width: 100%">
                <el-option
                  v-for="subject in subjects"
                  :key="subject"
                  :label="subject"
                  :value="subject"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="年级" prop="grade">
              <el-select v-model="form.grade" placeholder="选择年级" style="width: 100%">
                <el-option
                  v-for="grade in grades"
                  :key="grade"
                  :label="grade"
                  :value="grade"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="课题/主题" prop="topic">
              <el-input
                v-model="form.topic"
                placeholder="请输入课题或主题名称"
                clearable
              />
            </el-form-item>
            
            <el-form-item label="课时" prop="duration">
              <el-slider v-model="form.duration" :min="1" :max="4" show-stops />
              <div class="slider-label">{{ form.duration }} 课时</div>
            </el-form-item>
            
            <el-form-item label="班级规模" prop="classSize">
              <el-input-number v-model="form.classSize" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
            
            <el-form-item label="教学目标" prop="teachingGoals">
              <el-input
                v-model="form.teachingGoals"
                type="textarea"
                :rows="3"
                placeholder="描述您希望达到的教学目标..."
              />
            </el-form-item>
            
            <el-form-item label="特殊要求">
              <el-input
                v-model="form.requirements"
                type="textarea"
                :rows="3"
                placeholder="如有特殊要求请在此说明，如：需要融入多媒体、小组讨论等..."
              />
            </el-form-item>
            
            <el-form-item>
              <el-button
                type="primary"
                size="large"
                :icon="MagicStick"
                @click="generateLessonPlan"
                :loading="generating"
                style="width: 100%"
              >
                {{ generating ? '生成中...' : '智能生成教案' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 历史记录 -->
        <el-card class="history-card" shadow="hover" style="margin-top: 20px">
          <template #header>
            <div class="card-header">
              <span>生成历史</span>
              <el-button type="primary" text>查看全部</el-button>
            </div>
          </template>
          <el-scrollbar height="200px">
            <div
              v-for="plan in lessonPlanStore.lessonPlans.slice(0, 5)"
              :key="plan.id"
              class="history-item"
              @click="viewPlan(plan)"
            >
              <el-icon><Document /></el-icon>
              <div class="history-info">
                <div class="history-title">{{ plan.title }}</div>
                <div class="history-time">{{ formatDate(plan.createdAt) }}</div>
              </div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
      
      <!-- 右侧：预览/编辑区域 -->
      <el-col :span="16">
        <el-card v-if="!currentPlan" class="empty-preview" shadow="hover">
          <div class="empty-content">
            <el-icon size="80" color="#dcdfe6"><Document /></el-icon>
            <h2>智能教案生成</h2>
            <p>在左侧填写教学参数，AI 将为您生成完整的教案</p>
            <div class="features">
              <div class="feature-item">
                <el-icon size="24" color="#409eff"><Timer /></el-icon>
                <span>节省时间</span>
              </div>
              <div class="feature-item">
                <el-icon size="24" color="#67c23a"><CircleCheck /></el-icon>
                <span>专业规范</span>
              </div>
              <div class="feature-item">
                <el-icon size="24" color="#e6a23c"><Edit /></el-icon>
                <span>可编辑调整</span>
              </div>
            </div>
          </div>
        </el-card>
        
        <el-card v-else class="plan-preview" shadow="hover">
          <template #header>
            <div class="preview-header">
              <div class="preview-title">
                <el-input
                  v-model="currentPlan.title"
                  class="title-input"
                  placeholder="教案标题"
                />
              </div>
              <div class="preview-actions">
                <el-button type="primary" :icon="Edit">编辑</el-button>
                <el-button type="success" :icon="Download" @click="exportPlan">导出</el-button>
                <el-button type="warning" :icon="Share">分享</el-button>
                <el-button :icon="Printer">打印</el-button>
              </div>
            </div>
          </template>
          
          <el-scrollbar height="calc(100vh - 280px)">
            <div class="plan-content">
              <!-- 基本信息 -->
              <div class="plan-section">
                <h3><el-icon><InfoFilled /></el-icon> 基本信息</h3>
                <el-descriptions :column="2" border>
                  <el-descriptions-item label="学科">{{ currentPlan.subject }}</el-descriptions-item>
                  <el-descriptions-item label="年级">{{ currentPlan.grade }}</el-descriptions-item>
                  <el-descriptions-item label="课时">{{ currentPlan.duration }} 课时</el-descriptions-item>
                  <el-descriptions-item label="授课时间">{{ formatDate(Date.now()) }}</el-descriptions-item>
                </el-descriptions>
              </div>
              
              <!-- 教学目标 -->
              <div class="plan-section">
                <h3><el-icon><Aim /></el-icon> 教学目标</h3>
                <div class="editable-list">
                  <div
                    v-for="(_, index) in currentPlan.objectives"
                    :key="index"
                    class="list-item"
                  >
                    <span class="item-number">{{ index + 1 }}.</span>
                    <el-input v-model="currentPlan.objectives[index]" />
                    <el-button type="danger" :icon="Delete" circle size="small" @click="removeObjective(index)" />
                  </div>
                  <el-button type="primary" text :icon="Plus" @click="addObjective">添加目标</el-button>
                </div>
              </div>
              
              <!-- 教学重难点 -->
              <div class="plan-section">
                <h3><el-icon><WarningFilled /></el-icon> 教学重难点</h3>
                <el-row :gutter="20">
                  <el-col :span="12">
                    <h4>重点</h4>
                    <div class="editable-list">
                      <div
                        v-for="(_, index) in currentPlan.keyPoints"
                        :key="index"
                        class="list-item"
                      >
                        <el-input v-model="currentPlan.keyPoints[index]" />
                        <el-button type="danger" :icon="Delete" circle size="small" @click="removeKeyPoint(index)" />
                      </div>
                      <el-button type="primary" text :icon="Plus" @click="addKeyPoint">添加重点</el-button>
                    </div>
                  </el-col>
                  <el-col :span="12">
                    <h4>难点</h4>
                    <div class="editable-list">
                      <div
                        v-for="(_, index) in currentPlan.difficulties"
                        :key="index"
                        class="list-item"
                      >
                        <el-input v-model="currentPlan.difficulties[index]" />
                        <el-button type="danger" :icon="Delete" circle size="small" @click="removeDifficulty(index)" />
                      </div>
                      <el-button type="primary" text :icon="Plus" @click="addDifficulty">添加难点</el-button>
                    </div>
                  </el-col>
                </el-row>
              </div>
              
              <!-- 教学过程 -->
              <div class="plan-section">
                <h3><el-icon><List /></el-icon> 教学过程</h3>
                <el-timeline>
                  <el-timeline-item
                    v-for="(procedure, index) in currentPlan.procedures"
                    :key="index"
                    :type="getProcedureType(index)"
                    :timestamp="`${procedure.duration}分钟`"
                  >
                    <el-card shadow="hover" class="procedure-card">
                      <template #header>
                        <div class="procedure-header">
                          <el-input v-model="procedure.stage" class="stage-input" />
                          <el-input-number v-model="procedure.duration" :min="1" :max="120" />
                          <span>分钟</span>
                        </div>
                      </template>
                      <div class="procedure-content">
                        <div class="form-group">
                          <label>教学内容</label>
                          <el-input v-model="procedure.content" type="textarea" :rows="2" />
                        </div>
                        <div class="form-group">
                          <label>师生活动</label>
                          <el-input v-model="procedure.activities" type="textarea" :rows="2" />
                        </div>
                        <div class="form-group">
                          <label>设计意图</label>
                          <el-input v-model="procedure.designIntent" type="textarea" :rows="2" />
                        </div>
                      </div>
                    </el-card>
                  </el-timeline-item>
                </el-timeline>
                <el-button type="primary" :icon="Plus" @click="addProcedure">添加教学环节</el-button>
              </div>
              
              <!-- 作业布置 -->
              <div class="plan-section">
                <h3><el-icon><Notebook /></el-icon> 作业布置</h3>
                <el-input v-model="currentPlan.homework" type="textarea" :rows="4" />
              </div>
              
              <!-- 教学反思 -->
              <div class="plan-section">
                <h3><el-icon><ChatLineSquare /></el-icon> 教学反思</h3>
                <el-input v-model="currentPlan.reflection" type="textarea" :rows="4" placeholder="课后填写..." />
              </div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useLessonPlanStore, type LessonPlan } from '../stores/lessonPlan'
import { ElMessage } from 'element-plus'
import {
  Document,
  MagicStick,
  Edit,
  Download,
  Share,
  Printer,
  Plus,
  Delete,
  InfoFilled,
  Aim,
  WarningFilled,
  List,
  Notebook,
  ChatLineSquare,
  Timer,
  CircleCheck
} from '@element-plus/icons-vue'

const lessonPlanStore = useLessonPlanStore()
const formRef = ref()
const generating = ref(false)

const form = reactive({
  subject: '',
  grade: '',
  topic: '',
  duration: 1,
  classSize: 40,
  teachingGoals: '',
  requirements: ''
})

const rules = {
  subject: [{ required: true, message: '请选择学科', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  topic: [{ required: true, message: '请输入课题', trigger: 'blur' }]
}

const subjects = ['语文', '数学', '英语', '物理', '化学', '生物', '历史', '地理', '政治', '音乐', '美术', '体育', '信息技术']
const grades = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级', '初一', '初二', '初三', '高一', '高二', '高三']

const currentPlan = ref<LessonPlan | null>(null)

const generateLessonPlan = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  generating.value = true
  
  // 模拟 AI 生成
  setTimeout(() => {
    const plan: LessonPlan = {
      id: Date.now().toString(),
      title: `${form.grade}${form.subject} - ${form.topic}`,
      subject: form.subject,
      grade: form.grade,
      duration: form.duration,
      objectives: [
        '知识与技能：掌握核心概念和基本方法',
        '过程与方法：培养分析问题和解决问题的能力',
        '情感态度与价值观：激发学习兴趣，培养科学态度'
      ],
      keyPoints: ['核心知识点的理解和掌握', '基本方法的运用'],
      difficulties: ['知识点的深入理解', '实际问题的分析和解决'],
      teachingMethods: ['讲授法', '讨论法', '演示法', '练习法'],
      teachingAids: ['多媒体课件', '实物教具', '练习册'],
      procedures: [
        {
          stage: '导入新课',
          duration: 5,
          content: '通过生活实例引入课题，激发学生兴趣',
          activities: '教师展示案例，学生观察思考',
          designIntent: '创设情境，引发学习兴趣'
        },
        {
          stage: '新课讲授',
          duration: 20,
          content: '讲解核心概念，配合例题分析',
          activities: '教师讲解，学生听讲、记笔记、回答问题',
          designIntent: '系统传授知识，确保理解'
        },
        {
          stage: '课堂练习',
          duration: 10,
          content: '学生独立完成练习题，巩固所学',
          activities: '学生练习，教师巡视指导',
          designIntent: '及时巩固，发现问题'
        },
        {
          stage: '小结作业',
          duration: 5,
          content: '总结本节课内容，布置课后作业',
          activities: '师生共同总结，记录作业',
          designIntent: '梳理知识，延伸学习'
        }
      ],
      homework: '1. 完成课后练习题 1-5\n2. 预习下节课内容\n3. 收集生活中的相关实例',
      reflection: '',
      createdAt: Date.now()
    }
    
    currentPlan.value = plan
    lessonPlanStore.lessonPlans.unshift(plan)
    generating.value = false
    ElMessage.success('教案生成成功！')
  }, 2000)
}

const viewPlan = (plan: LessonPlan) => {
  currentPlan.value = plan
}

const exportPlan = () => {
  ElMessage.success('教案导出成功！')
}

// 编辑功能
const addObjective = () => currentPlan.value?.objectives.push('')
const removeObjective = (index: number) => currentPlan.value?.objectives.splice(index, 1)
const addKeyPoint = () => currentPlan.value?.keyPoints.push('')
const removeKeyPoint = (index: number) => currentPlan.value?.keyPoints.splice(index, 1)
const addDifficulty = () => currentPlan.value?.difficulties.push('')
const removeDifficulty = (index: number) => currentPlan.value?.difficulties.splice(index, 1)

const addProcedure = () => {
  currentPlan.value?.procedures.push({
    stage: '新环节',
    duration: 10,
    content: '',
    activities: '',
    designIntent: ''
  })
}

const getProcedureType = (index: number) => {
  const types = ['primary', 'success', 'warning', 'danger', 'info'] as const
  return types[index % types.length]
}

const formatDate = (timestamp: number) => {
  return new Date(timestamp).toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.lesson-plan-generator {
  .generate-form {
    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
    }
    
    .slider-label {
      text-align: center;
      color: #666;
      margin-top: 8px;
    }
  }
  
  .history-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .history-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      cursor: pointer;
      border-radius: 8px;
      transition: background 0.3s;
      
      &:hover {
        background: #f5f7fa;
      }
      
      .history-info {
        flex: 1;
        
        .history-title {
          font-size: 14px;
          color: #333;
          margin-bottom: 4px;
        }
        
        .history-time {
          font-size: 12px;
          color: #999;
        }
      }
    }
  }
  
  .empty-preview {
    height: calc(100vh - 140px);
    
    :deep(.el-card__body) {
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .empty-content {
      text-align: center;
      
      h2 {
        margin: 24px 0 12px;
        font-size: 24px;
        color: #333;
      }
      
      p {
        color: #999;
        margin-bottom: 40px;
      }
      
      .features {
        display: flex;
        justify-content: center;
        gap: 40px;
        
        .feature-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          
          span {
            font-size: 14px;
            color: #666;
          }
        }
      }
    }
  }
  
  .plan-preview {
    height: calc(100vh - 140px);
    
    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .preview-title {
        flex: 1;
        margin-right: 20px;
        
        .title-input {
          :deep(.el-input__inner) {
            font-size: 18px;
            font-weight: 600;
          }
        }
      }
      
      .preview-actions {
        display: flex;
        gap: 8px;
      }
    }
    
    .plan-content {
      padding: 20px;
      
      .plan-section {
        margin-bottom: 32px;
        
        h3 {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 18px;
          margin-bottom: 16px;
          color: #333;
          padding-bottom: 12px;
          border-bottom: 2px solid #e4e7ed;
        }
        
        h4 {
          font-size: 14px;
          color: #666;
          margin-bottom: 12px;
        }
        
        .editable-list {
          .list-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
            
            .item-number {
              color: #409eff;
              font-weight: 600;
            }
            
            .el-input {
              flex: 1;
            }
          }
        }
        
        .procedure-card {
          margin-bottom: 16px;
          
          .procedure-header {
            display: flex;
            align-items: center;
            gap: 12px;
            
            .stage-input {
              flex: 1;
              
              :deep(.el-input__inner) {
                font-weight: 600;
              }
            }
          }
          
          .procedure-content {
            .form-group {
              margin-bottom: 16px;
              
              label {
                display: block;
                font-size: 14px;
                color: #666;
                margin-bottom: 8px;
              }
            }
          }
        }
      }
    }
  }
}
</style>
