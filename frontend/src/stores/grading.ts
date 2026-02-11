import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface GradingTask {
  id: string
  title: string
  subject: string
  grade: string
  type: 'essay' | 'code' | 'math' | 'english' | 'other'
  rubric: RubricItem[]
  submissions: Submission[]
  createdAt: number
  status: 'pending' | 'processing' | 'completed'
}

export interface RubricItem {
  id?: string
  criteria: string
  weight: number
  description: string
}

export interface Submission {
  id: string
  studentName: string
  studentId: string
  content: string
  fileUrl?: string
  score?: number
  feedback?: Feedback
  submittedAt: number
  gradedAt?: number
}

export interface Feedback {
  overallScore: number
  overallComment: string
  strengths: string[]
  weaknesses: string[]
  suggestions: string[]
  criteriaScores: CriteriaScore[]
  detailedComments: string
}

export interface CriteriaScore {
  criteriaId: string
  score: number
  comment: string
}

export const useGradingStore = defineStore('grading', () => {
  const tasks = ref<GradingTask[]>([])
  const currentTask = ref<GradingTask | null>(null)
  const processing = ref(false)
  const batchSize = ref(10)

  const createTask = (params: { title: string; subject: string; grade: string; type: string; rubric: RubricItem[] }) => {
    const task: GradingTask = {
      title: params.title,
      subject: params.subject,
      grade: params.grade,
      type: params.type as 'essay' | 'code' | 'math' | 'english' | 'other',
      rubric: params.rubric,
      id: Date.now().toString(),
      submissions: [],
      createdAt: Date.now(),
      status: 'pending'
    }
    tasks.value.unshift(task)
    currentTask.value = task
    return task
  }

  const addSubmission = (taskId: string, submission: Omit<Submission, 'id' | 'submittedAt'>) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (task) {
      task.submissions.push({
        ...submission,
        id: Date.now().toString(),
        submittedAt: Date.now()
      })
    }
  }

  const gradeSubmission = async (taskId: string, submissionId: string) => {
    processing.value = true
    try {
      // 这里后续调用后端 API 进行 AI 批阅
      const task = tasks.value.find(t => t.id === taskId)
      if (!task) return
      const submission = task.submissions.find(s => s.id === submissionId)
      if (submission) {
        // 模拟 AI 批阅结果
        submission.feedback = {
          overallScore: 85,
          overallComment: '整体表现良好，思路清晰',
          strengths: ['逻辑清晰', '表达流畅'],
          weaknesses: ['细节不够完善', '举例不够丰富'],
          suggestions: ['增加具体案例', '深化分析'],
          criteriaScores: task.rubric.map(r => ({
            criteriaId: r.id || r.criteria,
            score: 85,
            comment: '符合要求'
          })),
          detailedComments: '这是一份优秀的作业...'
        }
        submission.gradedAt = Date.now()
      }
    } finally {
      processing.value = false
    }
  }

  const batchGrade = async (taskId: string) => {
    const task = tasks.value.find(t => t.id === taskId)
    if (!task) return
    
    task.status = 'processing'
    const ungraded = task.submissions.filter(s => !s.feedback)
    
    for (let i = 0; i < ungraded.length; i += batchSize.value) {
      const batch = ungraded.slice(i, i + batchSize.value)
      await Promise.all(batch.map(s => gradeSubmission(taskId, s.id)))
    }
    
    task.status = 'completed'
  }

  const deleteTask = (id: string) => {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index > -1) {
      tasks.value.splice(index, 1)
      if (currentTask.value?.id === id) {
        currentTask.value = null
      }
    }
  }

  return {
    tasks,
    currentTask,
    processing,
    batchSize,
    createTask,
    addSubmission,
    gradeSubmission,
    batchGrade,
    deleteTask
  }
})
