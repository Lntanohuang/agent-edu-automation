import axios from 'axios'
import { ElMessage } from 'element-plus'

export interface ApiResult<T> {
  code: number
  message: string
  data: T
  timestamp: string
}

// 与后端 Spring Data Page 对齐的分页结果
export interface SpringPage<T> {
  content: T[]
  totalElements: number
  number: number
  size: number
}

// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  nickname?: string
  email?: string
  phone?: string
  subjects?: string[]
}

export interface RefreshTokenRequest {
  refreshToken: string
}

export interface UserInfo {
  id: number
  username: string
  nickname: string
  avatar: string | null
  role: string
  subjects: string[]
}

export interface LoginResponse {
  token: string
  refreshToken: string
  expiresIn: number
  user: UserInfo
}

// 教案生成类型
export interface PlanAgentGeneratePayload {
  subject: string
  grade?: string
  topic?: string
  totalWeeks?: number
  lessonsPerWeek?: number
  classSize?: number
  courseType?: string
  credits?: number
  assessmentMode?: string
  teachingGoals?: string
  requirements?: string
  textbookVersion?: string
  difficulty?: string
  traceProjectName?: string
}

export interface PlanAgentGenerateData {
  success: boolean
  message: string
  semesterPlan: Record<string, unknown>
}

// V2 Multi-Agent Supervisor 教案类型
export interface AgentMeta {
  skill_status: Record<string, 'success' | 'degraded' | 'not_registered'>
  conflicts: string[]
  data_gaps: string[]
  merge_priority: Record<string, string>
  total_time_ms: number
}

export interface PlanAgentV2GenerateData {
  success: boolean
  message: string
  planId: number
  semesterPlan: Record<string, unknown>
  agentMeta: AgentMeta
}

export interface LessonPlanRecord {
  id: number
  userId: number
  title: string
  subject: string
  grade: string
  topic: string
  status: 'generated' | 'saved' | 'published'
  semesterPlanJson: string
  agentMetaJson: string
  createdAt: string
  updatedAt: string
}

export interface QuestionGeneratePayload {
  subject: string
  topic?: string
  textbookScope?: string[]
  questionCount?: number
  questionTypes?: string[]
  difficultyDistribution?: {
    easy: number
    medium: number
    hard: number
  }
  outputMode?: 'practice' | 'paper'
  totalScore?: number
  includeAnswer?: boolean
  includeExplanation?: boolean
  requireSourceCitation?: boolean
}

export interface QuestionGenerateData {
  draftId: number
  reviewStatus: string
  message: string
  generationMode: string
  questionCount: number
  questionSet: Record<string, unknown>
  bookLabels: string[]
  sources: string[]
  validationNotes: string[]
}

export interface QuestionDraftSummary {
  draftId: number
  title: string
  subject: string
  topic: string
  generationMode: string
  questionCount: number
  totalScore: number
  reviewStatus: string
  importedCount: number
  createdAt: string
  updatedAt: string
}

export interface QuestionDraftDetail extends QuestionDraftSummary {
  textbookScope: string[]
  reviewNote: string | null
  questionSet: {
    title?: string
    questions?: Array<Record<string, unknown>>
    total_score?: number
    question_count?: number
    output_mode?: string
  }
  bookLabels: string[]
  sources: string[]
  validationNotes: string[]
}

export interface QuestionReviewPayload {
  action: 'approve' | 'reject'
  reviewNote?: string
  editedQuestionSet?: Record<string, unknown>
}

export interface QuestionReviewData {
  draftId: number
  reviewStatus: string
  importedCount: number
  message: string
}

export interface QuestionBankItem {
  id: number
  draftId: number
  subject: string
  questionType: string
  difficulty: string
  stem: string
  options: string[]
  answer: string
  explanation: string
  knowledgePoints: string[]
  sourceCitations: Array<Record<string, unknown>>
  score: number
  status: string
  createdAt: string
}

export interface ChatMessagePayload {
  message: string
  conversationId?: number
  context?: Record<string, string>
}

export interface ChatMessageData {
  messageId: number
  conversationId: number
  content: string
  role: string
  timestamp: string
  tokens?: number
  skillUsed?: string
  sources?: string[]
  explorationTasks?: string[]
  bookLabels?: string[]
  confidence?: string
  auditNotes?: string[]
}

export interface ConversationData {
  id: number
  title: string
  lastMessage: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

export interface RagIndexByFilePayload {
  file: File
  chunkSize?: number
  chunkOverlap?: number
  bookLabel?: string
}

export interface RagIndexData {
  success: boolean
  message: string
  file_path: string
  doc_count: number
  chunk_count: number
  chunk_size: number
  chunk_overlap: number
  book_label?: string
  book_id?: string
  error?: string
}

export interface RagBookItem {
  book_id: string
  book_label: string
  file_name?: string
  chunk_count: number
}

export interface RagBookListData {
  success: boolean
  message: string
  total: number
  items: RagBookItem[]
  error?: string
}

export interface RagChatHistoryItem {
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  tool_call_id?: string
}

export interface RagAgentChatPayload {
  query: string
  conversation_id?: string
  history?: RagChatHistoryItem[]
  max_history_tokens?: number
  trace_project_name?: string
}

export interface RagAgentChatData {
  success: boolean
  message: string
  answer: string
  skill_used?: string
  sources: string[]
  exploration_tasks: string[]
  book_labels: string[]
  confidence: string
  audit_notes: string[]
  error?: string
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json'
  }
})

const aiApi = axios.create({
  baseURL: import.meta.env.VITE_AI_SERVICE_BASE_URL || 'http://localhost:8000',
  timeout: 120000
})

aiApi.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
)

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
    const requestUrl = String(error.config?.url || '')
    const isAuthRequest = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/register') || requestUrl.includes('/auth/refresh')
    const status = error.response?.status
    const message = error.response?.data?.message || '请求失败'
    ElMessage.error(message)
    
    // 401/403 统一按登录态失效处理，避免前端卡在 Forbidden
    if ((status === 401 || status === 403) && !isAuthRequest) {
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      window.location.href = '/login'
    }
    
    return Promise.reject(error)
  }
)

// 认证 API
export const authApi = {
  login: (params: LoginRequest) =>
    api.post<unknown, ApiResult<LoginResponse>>('/auth/login', params),
  
  register: (params: RegisterRequest) =>
    api.post<unknown, ApiResult<LoginResponse>>('/auth/register', params),
  
  refresh: (params: RefreshTokenRequest) =>
    api.post<unknown, ApiResult<LoginResponse>>('/auth/refresh', params),
  
  getCurrentUser: () =>
    api.get<unknown, ApiResult<UserInfo>>('/auth/me'),
  
  logout: () =>
    api.post<unknown, ApiResult<null>>('/auth/logout')
}

// 智能教案 API
export const lessonPlanApi = {
  generate: (params: PlanAgentGeneratePayload) =>
    api.post<unknown, ApiResult<PlanAgentGenerateData>>('/plan-agent/generate', params)
}

// V2 Multi-Agent Supervisor 教案 API
export const lessonPlanV2Api = {
  generate: (params: PlanAgentGeneratePayload) =>
    api.post<unknown, ApiResult<PlanAgentV2GenerateData>>('/plan-agent/v2/generate', params),
  getHistory: (page = 0, size = 20) =>
    api.get<unknown, ApiResult<SpringPage<LessonPlanRecord>>>('/plan-agent/v2/history', { params: { page, size } }),
  getById: (id: number) =>
    api.get<unknown, ApiResult<LessonPlanRecord>>(`/plan-agent/v2/${id}`),
  update: (id: number, data: Partial<LessonPlanRecord>) =>
    api.put<unknown, ApiResult<LessonPlanRecord>>(`/plan-agent/v2/${id}`, data),
  delete: (id: number) =>
    api.delete<unknown, ApiResult<void>>(`/plan-agent/v2/${id}`),
}

export const questionBankApi = {
  generate: (params: QuestionGeneratePayload) =>
    api.post<unknown, ApiResult<QuestionGenerateData>>('/question-bank/generate', params),

  listDrafts: (page = 1, size = 20) =>
    api.get<unknown, ApiResult<SpringPage<QuestionDraftSummary>>>('/question-bank/drafts', {
      params: { page, size }
    }),

  getDraftDetail: (draftId: number) =>
    api.get<unknown, ApiResult<QuestionDraftDetail>>(`/question-bank/drafts/${draftId}`),

  reviewDraft: (draftId: number, params: QuestionReviewPayload) =>
    api.post<unknown, ApiResult<QuestionReviewData>>(`/question-bank/drafts/${draftId}/review`, params),

  listItems: (page = 1, size = 20) =>
    api.get<unknown, ApiResult<SpringPage<QuestionBankItem>>>('/question-bank/items', {
      params: { page, size }
    })
}

// 智能问答 API
export const chatApi = {
  sendMessage: (params: ChatMessagePayload) =>
    api.post<unknown, ApiResult<ChatMessageData>>('/chat/message', params),

  getConversations: (page = 1, size = 20) =>
    api.get<unknown, ApiResult<SpringPage<ConversationData> | { list: ConversationData[]; total: number; page: number; size: number }>>(
      '/chat/conversations',
      { params: { page, size } }
    ),

  getMessages: (conversationId: number) =>
    api.get<unknown, ApiResult<ChatMessageData[]>>(`/chat/conversations/${conversationId}/messages`),

  deleteConversation: (conversationId: number) =>
    api.delete<unknown, ApiResult<null>>(`/chat/conversations/${conversationId}`),

  clearMessages: (conversationId: number) =>
    api.delete<unknown, ApiResult<null>>(`/chat/conversations/${conversationId}/messages`)
}

export const ragAiApi = {
  indexByFile: (payload: RagIndexByFilePayload) => {
    const formData = new FormData()
    formData.append('file', payload.file)
    formData.append('chunk_size', String(payload.chunkSize ?? 1000))
    formData.append('chunk_overlap', String(payload.chunkOverlap ?? 200))
    if (payload.bookLabel && payload.bookLabel.trim()) {
      formData.append('book_label', payload.bookLabel.trim())
    }
    return aiApi.post<unknown, RagIndexData>('/rag/index-by-file', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  listBooks: () =>
    aiApi.get<unknown, RagBookListData>('/rag/books'),
  agentChat: (payload: RagAgentChatPayload) =>
    aiApi.post<unknown, RagAgentChatData>('/rag/agent/chat', payload)
}

// 反馈 API
export interface FeedbackPayload {
  conversation_id: string
  message_id: string
  rating: 'helpful' | 'not_helpful'
  comment?: string
  confidence?: string
}

export const ragFeedbackApi = {
  submit: (payload: FeedbackPayload) =>
    aiApi.post<{ success: boolean; message: string }>('/feedback/', payload),
}

export default api
