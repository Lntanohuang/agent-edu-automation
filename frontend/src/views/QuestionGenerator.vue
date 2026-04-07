<template>
  <div class="question-generator page-view">
    <el-row :gutter="20">
      <el-col :span="8">
        <el-card shadow="hover" class="param-card">
          <template #header>
            <div class="card-header">
              <el-icon><EditPen /></el-icon>
              <span>智能出题参数</span>
            </div>
          </template>

          <el-form label-position="top">
            <el-form-item label="学科">
              <el-input v-model="form.subject" placeholder="劳动法" />
            </el-form-item>

            <el-form-item label="主题">
              <el-input v-model="form.topic" placeholder="教材重点章节" />
            </el-form-item>

            <el-form-item label="模式">
              <el-radio-group v-model="form.outputMode">
                <el-radio-button label="practice">练习题</el-radio-button>
                <el-radio-button label="paper">试卷</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item label="题量">
              <el-input-number v-model="form.questionCount" :min="1" :max="50" style="width: 100%" />
            </el-form-item>

            <el-form-item label="总分（试卷模式）">
              <el-input-number v-model="form.totalScore" :min="1" :max="300" style="width: 100%" />
            </el-form-item>

            <el-form-item label="题型">
              <el-checkbox-group v-model="form.questionTypes">
                <el-checkbox v-for="item in questionTypeOptions" :key="item" :label="item">{{ item }}</el-checkbox>
              </el-checkbox-group>
            </el-form-item>

            <el-form-item label="难度分布（%）">
              <div class="difficulty-grid">
                <el-input-number v-model="form.difficultyDistribution.easy" :min="0" :max="100" />
                <el-input-number v-model="form.difficultyDistribution.medium" :min="0" :max="100" />
                <el-input-number v-model="form.difficultyDistribution.hard" :min="0" :max="100" />
              </div>
              <div class="difficulty-tip">简单 / 中等 / 困难，总和建议为 100</div>
            </el-form-item>

            <el-form-item label="教材范围（可选）">
              <el-select
                v-model="form.textbookScope"
                multiple
                filterable
                collapse-tags
                placeholder="默认使用全部教材"
                style="width: 100%"
              >
                <el-option
                  v-for="book in books"
                  :key="book.book_id"
                  :label="book.book_label"
                  :value="book.book_label"
                />
              </el-select>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="generating" style="width: 100%" @click="handleGenerate">
                {{ generating ? '生成中...' : '生成题目草稿' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card shadow="hover" class="draft-card">
          <template #header>
            <div class="card-header">
              <span>出题草稿</span>
              <el-button text type="primary" @click="loadDrafts">刷新</el-button>
            </div>
          </template>

          <el-table :data="drafts" v-loading="draftLoading" size="small">
            <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="generationMode" label="模式" width="90">
              <template #default="{ row }">
                {{ row.generationMode === 'paper' ? '试卷' : '练习题' }}
              </template>
            </el-table-column>
            <el-table-column prop="questionCount" label="题量" width="80" />
            <el-table-column prop="reviewStatus" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTagType(row.reviewStatus)" size="small">{{ row.reviewStatus }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button text type="primary" @click="loadDraftDetail(row.draftId)">查看</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-card shadow="hover" class="detail-card" v-if="selectedDraft">
          <template #header>
            <div class="card-header">
              <div class="detail-title">
                <span>{{ selectedDraft.title }}</span>
                <el-tag :type="statusTagType(selectedDraft.reviewStatus)" size="small">
                  {{ selectedDraft.reviewStatus }}
                </el-tag>
              </div>
              <div class="detail-actions" v-if="selectedDraft.reviewStatus === 'pending'">
                <el-button size="small" type="success" @click="handleReview('approve')">审核通过并入库</el-button>
                <el-button size="small" type="danger" @click="handleReview('reject')">驳回</el-button>
              </div>
            </div>
          </template>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="学科">{{ selectedDraft.subject }}</el-descriptions-item>
            <el-descriptions-item label="主题">{{ selectedDraft.topic }}</el-descriptions-item>
            <el-descriptions-item label="模式">
              {{ selectedDraft.generationMode === 'paper' ? '试卷' : '练习题' }}
            </el-descriptions-item>
            <el-descriptions-item label="题量">{{ selectedDraft.questionCount }}</el-descriptions-item>
            <el-descriptions-item label="总分">{{ selectedDraft.totalScore }}</el-descriptions-item>
            <el-descriptions-item label="入库数量">{{ selectedDraft.importedCount }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="selectedDraft.validationNotes?.length" class="mt16">
            <el-alert
              v-for="(note, idx) in selectedDraft.validationNotes"
              :key="idx"
              :title="note"
              type="warning"
              :closable="false"
              class="mb8"
            />
          </div>

          <el-collapse class="mt16">
            <el-collapse-item
              v-for="(question, index) in questionList"
              :key="index"
              :name="index"
              :title="`${index + 1}. ${textValue(question.question_type, '题目')} (${textValue(question.difficulty, '中等')})`"
            >
              <div class="question-item">
                <div class="question-block"><strong>题干：</strong>{{ textValue(question.stem, '') }}</div>
                <div class="question-block" v-if="arrayValue(question.options).length">
                  <strong>选项：</strong>
                  <div v-for="(opt, idx) in arrayValue(question.options)" :key="idx">{{ opt }}</div>
                </div>
                <div class="question-block"><strong>答案：</strong>{{ textValue(question.answer, '') }}</div>
                <div class="question-block"><strong>解析：</strong>{{ textValue(question.explanation, '') }}</div>
                <div class="question-block"><strong>分值：</strong>{{ textValue(question.score, 0) }}</div>
                <div class="question-block">
                  <strong>知识点：</strong>{{ arrayValue(question.knowledge_points).join(' / ') || '无' }}
                </div>
                <div class="question-block" v-if="arrayValue(question.source_citations).length">
                  <strong>出处：</strong>
                  <div v-for="(citation, idx) in arrayValue(question.source_citations)" :key="idx" class="citation">
                    {{ citation.book_label || '未知教材' }} | {{ citation.source || '-' }} | {{ citation.chapter_or_page || '-' }}
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>

        <el-card shadow="hover" class="bank-card">
          <template #header>
            <div class="card-header">
              <span>题库（已入库）</span>
              <el-button text type="primary" @click="loadBankItems">刷新</el-button>
            </div>
          </template>

          <el-table :data="bankItems" v-loading="bankLoading" size="small">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="questionType" label="题型" width="110" />
            <el-table-column prop="difficulty" label="难度" width="90" />
            <el-table-column prop="score" label="分值" width="80" />
            <el-table-column prop="stem" label="题干" min-width="320" show-overflow-tooltip />
            <el-table-column prop="createdAt" label="入库时间" width="180">
              <template #default="{ row }">{{ formatDate(row.createdAt) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  questionBankApi,
  ragAiApi,
  type QuestionDraftDetail,
  type QuestionDraftSummary,
  type QuestionBankItem,
  type RagBookItem
} from '../api'
import { EditPen } from '@element-plus/icons-vue'

const questionTypeOptions = ['单选题', '多选题', '判断题', '填空题', '简答题', '案例分析题']

const form = reactive({
  subject: '劳动法',
  topic: '教材重点章节',
  textbookScope: [] as string[],
  questionCount: 10,
  questionTypes: [...questionTypeOptions],
  difficultyDistribution: {
    easy: 20,
    medium: 60,
    hard: 20
  },
  outputMode: 'practice' as 'practice' | 'paper',
  totalScore: 100,
  includeAnswer: true,
  includeExplanation: true,
  requireSourceCitation: true
})

const books = ref<RagBookItem[]>([])
const drafts = ref<QuestionDraftSummary[]>([])
const selectedDraft = ref<QuestionDraftDetail | null>(null)
const bankItems = ref<QuestionBankItem[]>([])

const generating = ref(false)
const draftLoading = ref(false)
const bankLoading = ref(false)

const questionList = computed(() => {
  if (!selectedDraft.value?.questionSet?.questions) {
    return []
  }
  return selectedDraft.value.questionSet.questions
})

const loadBooks = async () => {
  try {
    const data = await ragAiApi.listBooks()
    if (data.success) {
      books.value = data.items || []
    }
  } catch (_error) {
    books.value = []
  }
}

const loadDrafts = async () => {
  draftLoading.value = true
  try {
    const res = await questionBankApi.listDrafts(1, 30)
    drafts.value = res.data.content || []
  } finally {
    draftLoading.value = false
  }
}

const loadDraftDetail = async (draftId: number) => {
  const res = await questionBankApi.getDraftDetail(draftId)
  selectedDraft.value = res.data
}

const loadBankItems = async () => {
  bankLoading.value = true
  try {
    const res = await questionBankApi.listItems(1, 50)
    bankItems.value = res.data.content || []
  } finally {
    bankLoading.value = false
  }
}

const handleGenerate = async () => {
  const sum =
    Number(form.difficultyDistribution.easy) +
    Number(form.difficultyDistribution.medium) +
    Number(form.difficultyDistribution.hard)
  if (sum <= 0) {
    ElMessage.warning('难度分布总和必须大于 0')
    return
  }
  if (!form.questionTypes.length) {
    ElMessage.warning('请至少选择一个题型')
    return
  }

  generating.value = true
  try {
    const res = await questionBankApi.generate({
      ...form,
      outputMode: form.outputMode
    })
    ElMessage.success(res.data.message || '生成成功')
    await loadDrafts()
    await loadDraftDetail(res.data.draftId)
  } finally {
    generating.value = false
  }
}

const handleReview = async (action: 'approve' | 'reject') => {
  if (!selectedDraft.value) {
    return
  }
  const confirmText = action === 'approve' ? '确认审核通过并入库？' : '确认驳回该草稿？'
  await ElMessageBox.confirm(confirmText, '提示', { type: 'warning' })
  const res = await questionBankApi.reviewDraft(selectedDraft.value.draftId, { action })
  ElMessage.success(res.data.message || '审核完成')
  await loadDrafts()
  await loadDraftDetail(selectedDraft.value.draftId)
  await loadBankItems()
}

const statusTagType = (status: string) => {
  if (status === 'approved') return 'success'
  if (status === 'rejected') return 'danger'
  return 'warning'
}

const textValue = (value: unknown, fallback: string | number) => {
  if (value === undefined || value === null) return fallback
  const text = String(value).trim()
  return text || fallback
}

const arrayValue = (value: unknown) => {
  if (!Array.isArray(value)) return []
  return value as Array<any>
}

const formatDate = (value: string) => {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString()
}

onMounted(async () => {
  await Promise.all([loadBooks(), loadDrafts(), loadBankItems()])
})
</script>

<style scoped lang="scss">
.question-generator {
  :deep(.el-row) {
    flex-wrap: nowrap;
  }

  .param-card,
  .draft-card,
  .detail-card,
  .bank-card {
    border-radius: 16px;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--text-primary);
  }

  .detail-title {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .detail-actions {
    display: flex;
    gap: 8px;
  }

  .draft-card,
  .detail-card,
  .bank-card {
    margin-bottom: 16px;
  }

  .difficulty-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    width: 100%;
  }

  .difficulty-tip {
    color: var(--text-tertiary);
    font-size: 12px;
    margin-top: 8px;
  }

  .question-item {
    line-height: 1.8;
  }

  .question-block {
    margin-bottom: 6px;
    word-break: break-word;
  }

  .citation {
    color: var(--text-secondary);
    font-size: 13px;
  }

  .mt16 {
    margin-top: 16px;
  }

  .mb8 {
    margin-bottom: 8px;
  }

  :deep(.el-form-item__label) {
    color: var(--text-secondary);
    font-weight: 520;
  }
}
</style>
