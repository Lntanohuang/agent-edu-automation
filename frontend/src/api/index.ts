import axios from 'axios'
import { ElMessage } from 'element-plus'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    ElMessage.error(error.response?.data?.message || '请求失败')
    return Promise.reject(error)
  }
)

// 智能问答 API
export const chatApi = {
  sendMessage: (message: string, conversationId?: string) => 
    api.post('/chat/message', { message, conversationId }),
  
  getConversations: () => 
    api.get('/chat/conversations'),
  
  getMessages: (conversationId: string) => 
    api.get(`/chat/conversations/${conversationId}/messages`),
  
  deleteConversation: (conversationId: string) => 
    api.delete(`/chat/conversations/${conversationId}`)
}

// 智能教案 API
export const lessonPlanApi = {
  generate: (params: any) => 
    api.post('/lesson-plan/generate', params),
  
  save: (plan: any) => 
    api.post('/lesson-plan/save', plan),
  
  getList: () => 
    api.get('/lesson-plan/list'),
  
  getDetail: (id: string) => 
    api.get(`/lesson-plan/${id}`),
  
  delete: (id: string) => 
    api.delete(`/lesson-plan/${id}`),
  
  export: (id: string, format: 'pdf' | 'word') => 
    api.get(`/lesson-plan/${id}/export?format=${format}`, { responseType: 'blob' })
}

// 智能批阅 API
export const gradingApi = {
  createTask: (params: any) => 
    api.post('/grading/tasks', params),
  
  submitWork: (taskId: string, submission: any) => 
    api.post(`/grading/tasks/${taskId}/submissions`, submission),
  
  grade: (taskId: string, submissionId: string) => 
    api.post(`/grading/tasks/${taskId}/submissions/${submissionId}/grade`),
  
  batchGrade: (taskId: string) => 
    api.post(`/grading/tasks/${taskId}/batch-grade`),
  
  getTasks: () => 
    api.get('/grading/tasks'),
  
  getTaskDetail: (taskId: string) => 
    api.get(`/grading/tasks/${taskId}`),
  
  getResults: (taskId: string) => 
    api.get(`/grading/tasks/${taskId}/results`),
  
  exportResults: (taskId: string, format: 'excel' | 'pdf') => 
    api.get(`/grading/tasks/${taskId}/export?format=${format}`, { responseType: 'blob' })
}

export default api
