<template>
  <div class="lesson-plan-generator page-view">
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
            <el-form-item label="课程方向" prop="subject">
              <el-select
                v-model="form.subject"
                placeholder="可选择或手动输入课程方向"
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option
                  v-for="subject in subjects"
                  :key="subject"
                  :label="subject"
                  :value="subject"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="适用年级" prop="grade">
              <el-select
                v-model="form.grade"
                placeholder="可选择或手动输入适用年级"
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
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
                placeholder="如：物权变动、公平责任、行政复议程序"
                clearable
              />
            </el-form-item>
            
            <el-form-item label="每周学时" prop="duration">
              <el-slider v-model="form.duration" :min="1" :max="6" show-stops />
              <div class="slider-label">{{ form.duration }} 学时/周</div>
            </el-form-item>

            <el-form-item label="课程性质" prop="courseType">
              <el-select v-model="form.courseType" placeholder="选择课程性质" style="width: 100%">
                <el-option label="专业必修" value="专业必修" />
                <el-option label="专业选修" value="专业选修" />
                <el-option label="通识选修" value="通识选修" />
              </el-select>
            </el-form-item>

            <el-form-item label="课程学分" prop="credits">
              <el-input-number v-model="form.credits" :min="1" :max="8" style="width: 100%" />
            </el-form-item>
            
            <el-form-item label="班级规模" prop="classSize">
              <el-input-number v-model="form.classSize" :min="10" :max="300" style="width: 100%" />
            </el-form-item>

            <el-form-item label="考核方式" prop="assessmentMode">
              <el-select v-model="form.assessmentMode" placeholder="选择考核方式" style="width: 100%">
                <el-option label="期末闭卷 + 平时成绩" value="期末闭卷 + 平时成绩" />
                <el-option label="课程论文 + 课堂展示" value="课程论文 + 课堂展示" />
                <el-option label="案例分析 + 开卷考试" value="案例分析 + 开卷考试" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="能力目标（法学）" prop="teachingGoals">
              <el-input
                v-model="form.teachingGoals"
                type="textarea"
                :rows="3"
                placeholder="如：法条检索、案例分析、法律论证、庭审表达"
              />
            </el-form-item>
            
            <el-form-item label="教材与参考书" prop="textbookVersion">
              <el-input
                v-model="form.textbookVersion"
                placeholder="如：《民法学》（高教版）+《最高人民法院公报案例》"
              />
            </el-form-item>

            <el-form-item label="特殊要求（可选）">
              <el-input
                v-model="form.requirements"
                type="textarea"
                :rows="3"
                placeholder="如：每3周一次案例研讨；包含模拟法庭；结合最新司法解释"
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
                <el-icon size="24" color="var(--color-primary)"><Timer /></el-icon>
                <span>节省时间</span>
              </div>
              <div class="feature-item">
                <el-icon size="24" color="var(--color-accent)"><CircleCheck /></el-icon>
                <span>专业规范</span>
              </div>
              <div class="feature-item">
                <el-icon size="24" color="var(--text-secondary)"><Edit /></el-icon>
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
                <el-button :icon="Download" @click="exportPlan">导出</el-button>
                <el-button :icon="Share">分享</el-button>
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
                  <el-descriptions-item label="课程方向">{{ currentPlan.subject }}</el-descriptions-item>
                  <el-descriptions-item label="适用年级">{{ currentPlan.grade }}</el-descriptions-item>
                  <el-descriptions-item label="每周学时">{{ currentPlan.duration }} 学时</el-descriptions-item>
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
import { lessonPlanApi } from '../api'
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
  subject: '民法',
  grade: '法学本科二年级',
  topic: '',
  duration: 2,
  courseType: '专业必修',
  credits: 3,
  classSize: 60,
  assessmentMode: '期末闭卷 + 平时成绩',
  teachingGoals: '掌握法条检索、案例分析与法律论证能力',
  textbookVersion: '《民法学》（高教版）',
  requirements: ''
})

const rules = {
  subject: [{ required: true, message: '请输入或选择课程方向', trigger: 'change' }],
  grade: [{ required: true, message: '请输入或选择适用年级', trigger: 'change' }],
  topic: [{ required: true, message: '请输入课题', trigger: 'blur' }],
  courseType: [{ required: true, message: '请选择课程性质', trigger: 'change' }],
  assessmentMode: [{ required: true, message: '请选择考核方式', trigger: 'change' }]
}

const subjects = ['法理学', '宪法学', '民法', '刑法', '行政法与行政诉讼法', '民事诉讼法', '刑事诉讼法', '商法', '经济法', '国际法']
const grades = ['法学本科一年级', '法学本科二年级', '法学本科三年级', '法学本科四年级', '法学硕士']

const currentPlan = ref<LessonPlan | null>(null)

const toStringArray = (value: unknown): string[] => {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item))
}

const mapSemesterPlanToLessonPlan = (
  semesterPlan: Record<string, unknown>,
  fallback: { subject: string; grade: string; topic: string; duration: number }
): LessonPlan => {
  const weeklyPlans = Array.isArray(semesterPlan.weekly_plans)
    ? (semesterPlan.weekly_plans as Record<string, unknown>[])
    : []

  const mergedKeyPoints = weeklyPlans.flatMap((item) => toStringArray(item.key_points))
  const mergedDifficulties = weeklyPlans.flatMap((item) => toStringArray(item.difficulties))
  const mergedHomework = weeklyPlans
    .map((item) => item.homework)
    .filter((item) => item !== undefined && item !== null)
    .map((item) => String(item))

  const procedures = weeklyPlans.map((item) => ({
    stage: `第${String(item.week ?? '')}周 ${String(item.unit_topic ?? '')}`.trim(),
    duration: fallback.duration * 45,
    content: toStringArray(item.key_points).join('；') || '见周计划',
    activities: toStringArray(item.activities).join('；') || '见周计划',
    designIntent: toStringArray(item.objectives).join('；') || '达成周目标'
  }))

  return {
    id: Date.now().toString(),
    title: String(semesterPlan.semester_title || `${fallback.grade}${fallback.subject} - ${fallback.topic}`),
    subject: String(semesterPlan.subject || fallback.subject),
    grade: String(semesterPlan.grade || fallback.grade),
    duration: fallback.duration,
    objectives: toStringArray(semesterPlan.semester_goals),
    keyPoints: Array.from(new Set(mergedKeyPoints)),
    difficulties: Array.from(new Set(mergedDifficulties)),
    teachingMethods: toStringArray(semesterPlan.teaching_strategies),
    teachingAids: toStringArray(semesterPlan.resource_plan),
    procedures,
    homework: mergedHomework.join('\n') || '参考周计划作业安排',
    reflection: toStringArray(semesterPlan.assessment_plan).join('\n'),
    createdAt: Date.now()
  }
}

const generateLessonPlan = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  
  generating.value = true

  try {
    const response = await lessonPlanApi.generate({
      subject: form.subject,
      grade: form.grade,
      topic: form.topic,
      totalWeeks: 18,
      lessonsPerWeek: form.duration,
      classSize: form.classSize,
      courseType: form.courseType,
      credits: form.credits,
      assessmentMode: form.assessmentMode,
      teachingGoals: form.teachingGoals,
      requirements: `课程性质：${form.courseType}；考核方式：${form.assessmentMode}；课程学分：${form.credits}。${form.requirements || ''}`,
      textbookVersion: form.textbookVersion,
      difficulty: '大学法学'
    })

    const payload = response.data
    if (!payload.success) {
      throw new Error(payload.message || '教案生成失败')
    }

    const plan = mapSemesterPlanToLessonPlan(
      payload.semesterPlan || {},
      {
        subject: form.subject,
        grade: form.grade,
        topic: form.topic,
        duration: form.duration
      }
    )

    currentPlan.value = plan
    lessonPlanStore.lessonPlans.unshift(plan)
    ElMessage.success('教案生成成功！')
  } catch (error) {
    const message = error instanceof Error ? error.message : '教案生成失败'
    ElMessage.error(message)
  } finally {
    generating.value = false
  }
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
  :deep(.el-row) {
    flex-wrap: nowrap;
  }

  .generate-form {
    border-radius: 16px;

    .card-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 620;
      color: var(--text-primary);
    }

    .slider-label {
      text-align: center;
      color: var(--text-secondary);
      margin-top: 8px;
      font-size: 12px;
    }
  }

  .history-card {
    border-radius: 16px;

    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: var(--text-primary);
    }

    .history-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      cursor: pointer;
      border-radius: 10px;
      border: 1px solid transparent;
      transition: all 0.2s ease;

      &:hover {
        border-color: var(--border-color);
        background: var(--surface-2);
      }

      .history-info {
        flex: 1;

        .history-title {
          font-size: 14px;
          color: var(--text-primary);
          margin-bottom: 4px;
        }

        .history-time {
          font-size: 12px;
          color: var(--text-tertiary);
        }
      }
    }
  }

  .empty-preview {
    min-height: 720px;

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
        color: var(--text-primary);
      }

      p {
        color: var(--text-secondary);
        margin-bottom: 34px;
      }

      .features {
        display: flex;
        justify-content: center;
        gap: 34px;

        .feature-item {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;

          span {
            font-size: 14px;
            color: var(--text-secondary);
          }
        }
      }
    }
  }

  .plan-preview {
    min-height: 720px;

    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .preview-title {
        flex: 1;
        margin-right: 20px;

        .title-input {
          :deep(.el-input__wrapper) {
            box-shadow: none;
            border-color: transparent;
            background: transparent;
          }

          :deep(.el-input__inner) {
            font-size: 18px;
            font-weight: 620;
            color: var(--text-primary);
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
          color: var(--text-primary);
          padding-bottom: 10px;
          border-bottom: 1px solid var(--border-color);
        }

        h4 {
          font-size: 14px;
          color: var(--text-secondary);
          margin-bottom: 12px;
        }

        .editable-list {
          .list-item {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;

            .item-number {
              color: var(--color-accent);
              font-weight: 620;
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
                font-weight: 620;
              }
            }
          }

          .procedure-content {
            .form-group {
              margin-bottom: 16px;

              label {
                display: block;
                font-size: 14px;
                color: var(--text-secondary);
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
