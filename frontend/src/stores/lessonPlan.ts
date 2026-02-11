import { defineStore } from 'pinia'
import { ref } from 'vue'

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
  const history = ref<LessonPlan[]>([])

  const generateLessonPlan = async (params: LessonPlanParams): Promise<LessonPlan> => {
    generating.value = true
    try {
      // 这里后续调用后端 API
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
        createdAt: Date.now()
      }
      lessonPlans.value.unshift(plan)
      currentPlan.value = plan
      return plan
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

  return {
    lessonPlans,
    currentPlan,
    generating,
    history,
    generateLessonPlan,
    saveLessonPlan,
    deleteLessonPlan
  }
})
