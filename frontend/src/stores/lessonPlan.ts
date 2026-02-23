import { defineStore } from 'pinia'
import { ref } from 'vue'
import { lessonPlanApi, type PlanAgentGeneratePayload } from '../api'

export interface LessonPlan {
  id: string
  title: string
  subject: string
  grade: string
  duration: number
  objectives: string[]
  keyPoints: string[]
  difficulties: string[]
  teachingMethods: string[]
  teachingAids: string[]
  procedures: TeachingProcedure[]
  homework: string
  reflection: string
  createdAt: number
  semesterPlan?: Record<string, unknown> // 后端返回的完整教案数据
}

export interface TeachingProcedure {
  stage: string
  duration: number
  content: string
  activities: string
  designIntent: string
}

export interface LessonPlanParams {
  subject: string
  grade: string
  topic: string
  duration: number
  classSize: number
  teachingGoals: string
  requirements?: string
}

export const useLessonPlanStore = defineStore('lessonPlan', () => {
  const lessonPlans = ref<LessonPlan[]>([])
  const currentPlan = ref<LessonPlan | null>(null)
  const generating = ref(false)
  const error = ref<string | null>(null)

  const generateLessonPlan = async (params: LessonPlanParams): Promise<LessonPlan | null> => {
    generating.value = true
    error.value = null
    
    try {
      // 调用后端 API
      const payload: PlanAgentGeneratePayload = {
        subject: params.subject,
        grade: params.grade,
        topic: params.topic,
        totalWeeks: Math.ceil(params.duration / 2), // 假设每周2课时
        lessonsPerWeek: 2,
        classSize: params.classSize,
        teachingGoals: params.teachingGoals,
        requirements: params.requirements
      }
      
      const response = await lessonPlanApi.generate(payload)
      
      if (response.code !== 200 || !response.data.success) {
        throw new Error(response.data.message || '生成失败')
      }
      
      const plan: LessonPlan = {
        id: Date.now().toString(),
        title: `${params.grade}${params.subject} - ${params.topic}`,
        subject: params.subject,
        grade: params.grade,
        duration: params.duration,
        objectives: [],
        keyPoints: [],
        difficulties: [],
        teachingMethods: [],
        teachingAids: [],
        procedures: [],
        homework: '',
        reflection: '',
        createdAt: Date.now(),
        semesterPlan: response.data.semesterPlan
      }
      
      lessonPlans.value.unshift(plan)
      currentPlan.value = plan
      return plan
    } catch (err) {
      error.value = err instanceof Error ? err.message : '生成教案失败'
      console.error('生成教案失败:', err)
      return null
    } finally {
      generating.value = false
    }
  }

  const saveLessonPlan = (plan: LessonPlan) => {
    const index = lessonPlans.value.findIndex(p => p.id === plan.id)
    if (index > -1) {
      lessonPlans.value[index] = plan
    } else {
      lessonPlans.value.unshift(plan)
    }
  }

  const deleteLessonPlan = (id: string) => {
    const index = lessonPlans.value.findIndex(p => p.id === id)
    if (index > -1) {
      lessonPlans.value.splice(index, 1)
      if (currentPlan.value?.id === id) {
        currentPlan.value = null
      }
    }
  }

  const setCurrentPlan = (plan: LessonPlan | null) => {
    currentPlan.value = plan
  }

  return {
    lessonPlans,
    currentPlan,
    generating,
    error,
    generateLessonPlan,
    saveLessonPlan,
    deleteLessonPlan,
    setCurrentPlan
  }
})
