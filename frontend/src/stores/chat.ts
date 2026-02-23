import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import {
  chatApi,
  type ChatMessageData,
  type ConversationData,
  type SpringPage
} from '../api'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  skillUsed?: string
  sources?: string[]
  explorationTasks?: string[]
  bookLabels?: string[]
  confidence?: string
  auditNotes?: string[]
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
  updatedAt?: number
  isDraft?: boolean
}

interface ConversationListFallback {
  list: ConversationData[]
  total: number
  page: number
  size: number
}

const normalizeStringList = (value: unknown): string[] => {
  if (!Array.isArray(value)) return []
  return value.map((item) => String(item))
}

const parseTime = (value?: string): number => {
  if (!value) return Date.now()
  const time = Date.parse(value)
  return Number.isNaN(time) ? Date.now() : time
}

const mapMessage = (item: ChatMessageData): Message => ({
  id: String(item.messageId),
  role: item.role === 'assistant' ? 'assistant' : 'user',
  content: String(item.content || ''),
  timestamp: parseTime(item.timestamp),
  skillUsed: item.skillUsed,
  sources: normalizeStringList(item.sources),
  explorationTasks: normalizeStringList(item.explorationTasks),
  bookLabels: normalizeStringList(item.bookLabels),
  confidence: item.confidence,
  auditNotes: normalizeStringList(item.auditNotes)
})

const mapConversation = (item: ConversationData): Conversation => ({
  id: String(item.id),
  title: item.title || '新对话',
  messages: [],
  createdAt: parseTime(item.createdAt),
  updatedAt: parseTime(item.updatedAt)
})

const getConversationListFromPayload = (
  payload: SpringPage<ConversationData> | ConversationListFallback
): ConversationData[] => {
  if ('content' in payload) {
    return payload.content
  }
  return payload.list
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<string>('')
  const loading = ref(false)

  const currentConversation = computed(() =>
    conversations.value.find((c) => c.id === currentConversationId.value)
  )

  const loadConversationMessages = async (conversationId: string): Promise<void> => {
    const target = conversations.value.find((item) => item.id === conversationId)
    if (!target || target.isDraft) return
    const result = await chatApi.getMessages(Number(conversationId))
    target.messages = (result.data || []).map(mapMessage)
  }

  const createConversation = (): Conversation => {
    const conversation: Conversation = {
      id: `draft-${Date.now()}`,
      title: '新对话',
      messages: [],
      createdAt: Date.now(),
      isDraft: true
    }
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.id
    return conversation
  }

  const refreshConversations = async (): Promise<void> => {
    const messageCache = new Map(conversations.value.map((item) => [item.id, item.messages]))
    const drafts = conversations.value.filter((item) => item.isDraft)
    const result = await chatApi.getConversations(1, 50)
    const list = getConversationListFromPayload(result.data || { content: [], totalElements: 0, number: 0, size: 50 })
    const serverConversations = list.map(mapConversation)

    serverConversations.forEach((item) => {
      const cachedMessages = messageCache.get(item.id)
      if (cachedMessages) {
        item.messages = cachedMessages
      }
    })

    conversations.value = [...drafts, ...serverConversations]
    if (!currentConversationId.value && conversations.value.length > 0) {
      currentConversationId.value = conversations.value[0].id
    }
  }

  const selectConversation = async (id: string): Promise<void> => {
    currentConversationId.value = id
    await loadConversationMessages(id)
  }

  const sendMessage = async (content: string): Promise<void> => {
    const messageText = content.trim()
    if (!messageText) return

    let conversation = currentConversation.value
    if (!conversation) {
      conversation = createConversation()
    }

    const sendToConversationId = conversation.isDraft ? undefined : Number(conversation.id)
    const userMessage: Message = {
      id: `local-user-${Date.now()}`,
      role: 'user',
      content: messageText,
      timestamp: Date.now()
    }
    conversation.messages.push(userMessage)

    if (conversation.title === '新对话') {
      conversation.title = messageText.slice(0, 20)
    }

    const assistantMessage: Message = {
      id: `local-assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      timestamp: Date.now()
    }
    conversation.messages.push(assistantMessage)

    loading.value = true

    try {
      const result = await chatApi.sendMessage({
        message: messageText,
        conversationId: sendToConversationId
      })
      const reply = result.data
      if (!reply) {
        throw new Error('AI 服务未返回结果')
      }

      const conversationId = reply.conversationId
      if (conversationId !== undefined && conversationId !== null && conversation.isDraft) {
        conversation.id = String(conversationId)
        conversation.isDraft = false
        currentConversationId.value = conversation.id
      }
      assistantMessage.id = String(reply.messageId || assistantMessage.id)
      assistantMessage.content = (reply.content || '').trim()
      if (!assistantMessage.content) {
        throw new Error('AI 返回内容为空')
      }
      assistantMessage.timestamp = parseTime(reply.timestamp)
      assistantMessage.skillUsed = reply.skillUsed
      assistantMessage.sources = normalizeStringList(reply.sources)
      assistantMessage.explorationTasks = normalizeStringList(reply.explorationTasks)
      assistantMessage.bookLabels = normalizeStringList(reply.bookLabels)
      assistantMessage.confidence = reply.confidence
      assistantMessage.auditNotes = normalizeStringList(reply.auditNotes)

      const realConversationId = conversation.id
      try {
        await loadConversationMessages(realConversationId)
      } catch (syncError) {
        console.warn('同步消息历史失败', syncError)
      }

      try {
        await refreshConversations()
      } catch (syncError) {
        console.warn('刷新会话列表失败', syncError)
      }
    } catch (error) {
      conversation.messages = conversation.messages.filter((item) =>
        item.id !== assistantMessage.id && item.id !== userMessage.id
      )
      throw error
    } finally {
      loading.value = false
    }
  }

  const deleteConversation = async (id: string): Promise<void> => {
    const index = conversations.value.findIndex((c) => c.id === id)
    if (index < 0) return

    const target = conversations.value[index]
    if (!target.isDraft) {
      await chatApi.deleteConversation(Number(id))
    }

    conversations.value.splice(index, 1)
    if (currentConversationId.value === id) {
      currentConversationId.value = conversations.value[0]?.id || ''
    }
  }

  const clearMessages = async (id: string): Promise<void> => {
    const target = conversations.value.find((c) => c.id === id)
    if (!target) return

    if (!target.isDraft) {
      await chatApi.clearMessages(Number(id))
    }
    target.messages = []
  }

  return {
    conversations,
    currentConversationId,
    currentConversation,
    loading,
    createConversation,
    refreshConversations,
    selectConversation,
    sendMessage,
    deleteConversation,
    clearMessages
  }
})
