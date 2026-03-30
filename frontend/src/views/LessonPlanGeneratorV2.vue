<template>
  <div class="lesson-plan-v2">
    <el-row :gutter="20">
      <!-- 左侧：生成表单 -->
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>Multi-Agent 教案生成</span>
              <el-tag type="primary" size="small">Supervisor V2</el-tag>
            </div>
          </template>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-position="top"
            size="default"
          >
            <el-form-item label="学科" prop="subject">
              <el-select v-model="form.subject" placeholder="选择学科" style="width: 100%">
                <el-option v-for="s in subjects" :key="s" :label="s" :value="s" />
              </el-select>
            </el-form-item>

            <el-form-item label="年级" prop="grade">
              <el-select v-model="form.grade" placeholder="选择年级" style="width: 100%">
                <el-option v-for="g in grades" :key="g" :label="g" :value="g" />
              </el-select>
            </el-form-item>

            <el-form-item label="学期主题" prop="topic">
              <el-input v-model="form.topic" placeholder="如：物权变动、劳动合同" />
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="学期周数">
                  <el-input-number v-model="form.totalWeeks" :min="8" :max="24" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="每周课时">
                  <el-input-number v-model="form.lessonsPerWeek" :min="1" :max="6" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="课程性质">
              <el-select v-model="form.courseType" style="width: 100%">
                <el-option label="专业必修" value="专业必修" />
                <el-option label="专业选修" value="专业选修" />
                <el-option label="通识选修" value="通识选修" />
              </el-select>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="课程学分">
                  <el-input-number v-model="form.credits" :min="1" :max="8" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="班级人数">
                  <el-input-number v-model="form.classSize" :min="10" :max="300" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="考核方式">
              <el-select v-model="form.assessmentMode" style="width: 100%">
                <el-option label="期末闭卷 + 平时成绩" value="期末闭卷 + 平时成绩" />
                <el-option label="期末开卷 + 课程论文" value="期末开卷 + 课程论文" />
                <el-option label="全过程考核" value="全过程考核" />
              </el-select>
            </el-form-item>

            <el-form-item label="教学目标">
              <el-input v-model="form.teachingGoals" type="textarea" :rows="2" placeholder="法律思维、案例分析等" />
            </el-form-item>

            <el-form-item label="教材版本">
              <el-input v-model="form.textbookVersion" placeholder="如：《民法学》（高教版）" />
            </el-form-item>

            <el-form-item label="特殊要求">
              <el-input v-model="form.requirements" type="textarea" :rows="2" placeholder="可选" />
            </el-form-item>

            <el-button
              type="primary"
              :loading="generating"
              style="width: 100%"
              size="large"
              @click="handleGenerate"
            >
              {{ generating ? '生成中...' : '智能生成教案' }}
            </el-button>
          </el-form>
        </el-card>

        <!-- 历史记录 -->
        <el-card shadow="hover" style="margin-top: 16px" v-if="historyList.length > 0">
          <template #header>
            <span>历史教案</span>
          </template>
          <div
            v-for="item in historyList"
            :key="item.id"
            class="history-item"
            @click="loadHistoryPlan(item)"
          >
            <div class="history-title">{{ item.title }}</div>
            <div class="history-meta">
              <el-tag size="small" :type="item.status === 'published' ? 'success' : 'info'">
                {{ statusMap[item.status] || item.status }}
              </el-tag>
              <span class="history-date">{{ formatDate(item.createdAt) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：结果展示 -->
      <el-col :span="16">
        <!-- Agent 执行状态面板 -->
        <el-card v-if="agentMeta || generating" shadow="hover" class="agent-panel">
          <template #header>
            <div class="card-header">
              <span>Multi-Agent 执行状态</span>
              <el-tag v-if="agentMeta" size="small">
                耗时 {{ (agentMeta.total_time_ms / 1000).toFixed(1) }}s
              </el-tag>
            </div>
          </template>

          <div class="skill-status-list">
            <div v-for="(label, key) in skillLabels" :key="key" class="skill-status-item">
              <span class="skill-icon">
                <template v-if="generating && !agentMeta">
                  <el-icon class="is-loading"><Loading /></el-icon>
                </template>
                <template v-else-if="agentMeta">
                  <template v-if="agentMeta.skill_status[key] === 'success'">
                    <el-icon color="#67c23a"><CircleCheckFilled /></el-icon>
                  </template>
                  <template v-else-if="agentMeta.skill_status[key] === 'degraded'">
                    <el-icon color="#e6a23c"><WarningFilled /></el-icon>
                  </template>
                  <template v-else>
                    <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
                  </template>
                </template>
              </span>
              <span class="skill-label">{{ label }}</span>
              <el-tag
                v-if="agentMeta"
                :type="agentMeta.skill_status[key] === 'success' ? 'success' : agentMeta.skill_status[key] === 'degraded' ? 'warning' : 'danger'"
                size="small"
              >
                {{ agentMeta.skill_status[key] === 'success' ? '成功' : agentMeta.skill_status[key] === 'degraded' ? '降级' : '未注册' }}
              </el-tag>
              <el-tag v-else-if="generating" type="info" size="small">执行中</el-tag>
            </div>
          </div>
        </el-card>

        <!-- 降级警告 -->
        <el-alert
          v-if="agentMeta && agentMeta.data_gaps.length > 0"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px"
        >
          <template #title>
            部分模块降级
          </template>
          <template #default>
            以下模块生成失败，相关内容标注为 [数据缺失]，建议人工补充：
            <strong>{{ agentMeta.data_gaps.map(g => skillLabels[g] || g).join('、') }}</strong>
          </template>
        </el-alert>

        <!-- 冲突标注 -->
        <el-alert
          v-for="(conflict, idx) in (agentMeta?.conflicts || [])"
          :key="idx"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 12px"
        >
          <template #title>冲突检测</template>
          <template #default>{{ conflict }}</template>
        </el-alert>

        <!-- 教案内容 -->
        <el-card v-if="semesterPlan" shadow="hover" class="plan-content">
          <template #header>
            <div class="card-header">
              <span>{{ planTitle }}</span>
              <div>
                <el-tag type="success" size="small" style="margin-right: 8px">
                  共 {{ weeklyPlans.length }} 周
                </el-tag>
              </div>
            </div>
          </template>

          <!-- 学期目标 -->
          <div v-if="semesterGoals.length > 0" class="section">
            <h4>学期目标</h4>
            <ul>
              <li v-for="(goal, i) in semesterGoals" :key="i">{{ goal }}</li>
            </ul>
          </div>

          <!-- 教学策略 -->
          <div v-if="teachingStrategies.length > 0" class="section">
            <h4>教学策略</h4>
            <ul>
              <li v-for="(s, i) in teachingStrategies" :key="i">{{ s }}</li>
            </ul>
          </div>

          <!-- 周计划表格 -->
          <div class="section">
            <h4>每周教学安排</h4>
            <el-table :data="weeklyPlans" stripe border style="width: 100%">
              <el-table-column prop="week" label="周次" width="70" align="center" />
              <el-table-column prop="unit_topic" label="单元主题" min-width="140" />
              <el-table-column label="教学目标" min-width="200">
                <template #default="{ row }">
                  <ul class="compact-list">
                    <li v-for="(o, i) in (row.objectives || [])" :key="i">{{ o }}</li>
                  </ul>
                </template>
              </el-table-column>
              <el-table-column label="重点" min-width="150">
                <template #default="{ row }">
                  <el-tag v-for="(k, i) in (row.key_points || [])" :key="i" size="small" style="margin: 2px">
                    {{ k }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="活动" min-width="160">
                <template #default="{ row }">
                  <ul class="compact-list">
                    <li v-for="(a, i) in (row.activities || [])" :key="i">{{ a }}</li>
                  </ul>
                </template>
              </el-table-column>
              <el-table-column prop="homework" label="作业" min-width="120" />
              <el-table-column prop="assessment" label="考核" min-width="100" />
            </el-table>
          </div>

          <!-- 考核方案 -->
          <div v-if="assessmentPlan.length > 0" class="section">
            <h4>学期考核方案</h4>
            <ul>
              <li v-for="(a, i) in assessmentPlan" :key="i">{{ a }}</li>
            </ul>
          </div>
        </el-card>

        <!-- 空状态 -->
        <el-card v-if="!semesterPlan && !generating" shadow="hover">
          <el-empty description="Multi-Agent Supervisor 教案生成">
            <template #image>
              <div style="font-size: 48px">&#129302;</div>
            </template>
            <div class="empty-features">
              <p><strong>4 个专家 Agent 并行工作</strong></p>
              <p>课程大纲 / 知识排序 / 教学活动 / 考核设计</p>
              <p>独立上下文，重试降级不阻塞，冲突自动检测</p>
            </div>
          </el-empty>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheckFilled, WarningFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import { lessonPlanV2Api } from '@/api/index'
import type { AgentMeta, LessonPlanRecord } from '@/api/index'

interface WeeklyPlan {
  week: number
  unit_topic: string
  objectives: string[]
  key_points: string[]
  difficulties: string[]
  activities: string[]
  homework: string
  assessment: string
}

const formRef = ref<FormInstance>()
const generating = ref(false)
const semesterPlan = ref<Record<string, unknown> | null>(null)
const agentMeta = ref<AgentMeta | null>(null)
const historyList = ref<LessonPlanRecord[]>([])

const form = ref({
  subject: '劳动法',
  grade: '法学本科三年级',
  topic: '',
  totalWeeks: 18,
  lessonsPerWeek: 2,
  classSize: 40,
  courseType: '专业必修',
  credits: 3,
  assessmentMode: '期末闭卷 + 平时成绩',
  teachingGoals: '',
  textbookVersion: '',
  requirements: '',
})

const subjects = ['民法', '刑法', '宪法', '行政法', '劳动法', '商法', '经济法', '知识产权法', '国际法', '法理学']
const grades = ['法学本科一年级', '法学本科二年级', '法学本科三年级', '法学本科四年级', '法学硕士']

const statusMap: Record<string, string> = {
  generated: '已生成',
  saved: '已保存',
  published: '已发布',
}

const skillLabels: Record<string, string> = {
  curriculum_outline: '课程大纲分析',
  knowledge_sequencing: '知识点排序',
  teaching_activity: '教学活动设计',
  assessment_design: '考核方案设计',
}

const rules: FormRules = {
  subject: [{ required: true, message: '请选择学科', trigger: 'change' }],
  grade: [{ required: true, message: '请选择年级', trigger: 'change' }],
  topic: [{ required: true, message: '请输入学期主题', trigger: 'blur' }],
}

const planTitle = computed(() => {
  if (!semesterPlan.value) return ''
  return (semesterPlan.value.semester_title as string) || `${form.value.subject} 学期教案`
})

const weeklyPlans = computed<WeeklyPlan[]>(() => {
  if (!semesterPlan.value) return []
  return (semesterPlan.value.weekly_plans as WeeklyPlan[]) || []
})

const semesterGoals = computed<string[]>(() => {
  if (!semesterPlan.value) return []
  return (semesterPlan.value.semester_goals as string[]) || []
})

const teachingStrategies = computed<string[]>(() => {
  if (!semesterPlan.value) return []
  return (semesterPlan.value.teaching_strategies as string[]) || []
})

const assessmentPlan = computed<string[]>(() => {
  if (!semesterPlan.value) return []
  return (semesterPlan.value.assessment_plan as string[]) || []
})

function formatDate(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function handleGenerate() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  generating.value = true
  semesterPlan.value = null
  agentMeta.value = null

  try {
    const res = await lessonPlanV2Api.generate({
      subject: form.value.subject,
      grade: form.value.grade,
      topic: form.value.topic,
      totalWeeks: form.value.totalWeeks,
      lessonsPerWeek: form.value.lessonsPerWeek,
      classSize: form.value.classSize,
      courseType: form.value.courseType,
      credits: form.value.credits,
      assessmentMode: form.value.assessmentMode,
      teachingGoals: form.value.teachingGoals || undefined,
      textbookVersion: form.value.textbookVersion || undefined,
      requirements: form.value.requirements || undefined,
    })

    const data = res.data
    if (data.success) {
      semesterPlan.value = data.semesterPlan
      agentMeta.value = data.agentMeta
      ElMessage.success('教案生成成功')
      loadHistory()
    } else {
      ElMessage.error(data.message || '生成失败')
    }
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '请求失败'
    ElMessage.error(msg)
  } finally {
    generating.value = false
  }
}

function loadHistoryPlan(item: LessonPlanRecord) {
  try {
    semesterPlan.value = JSON.parse(item.semesterPlanJson || '{}')
    agentMeta.value = item.agentMetaJson ? JSON.parse(item.agentMetaJson) : null
  } catch {
    ElMessage.error('解析历史教案失败')
  }
}

async function loadHistory() {
  try {
    const res = await lessonPlanV2Api.getHistory(0, 10)
    historyList.value = res.data?.content || []
  } catch {
    // 静默失败
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped lang="scss">
.lesson-plan-v2 {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-panel {
  margin-bottom: 16px;
}

.skill-status-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skill-status-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}

.skill-icon {
  display: flex;
  align-items: center;
  font-size: 18px;
}

.skill-label {
  flex: 1;
  font-size: 14px;
}

.plan-content {
  margin-bottom: 16px;
}

.section {
  margin-bottom: 24px;

  h4 {
    margin-bottom: 12px;
    color: var(--el-text-color-primary);
    font-size: 15px;
    border-left: 3px solid var(--el-color-primary);
    padding-left: 8px;
  }

  ul {
    padding-left: 20px;
    margin: 0;
    li {
      margin-bottom: 4px;
      line-height: 1.6;
    }
  }
}

.compact-list {
  padding-left: 16px;
  margin: 0;
  li {
    font-size: 13px;
    line-height: 1.5;
  }
}

.history-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;

  &:hover {
    background: var(--el-fill-color-light);
  }

  &:last-child {
    border-bottom: none;
  }
}

.history-title {
  font-size: 14px;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.empty-features {
  text-align: center;
  color: var(--el-text-color-secondary);
  p {
    margin: 4px 0;
  }
}
</style>
