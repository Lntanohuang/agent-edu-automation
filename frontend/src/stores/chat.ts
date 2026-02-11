import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
  loading?: boolean
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
}

export const useChatStore = defineStore('chat', () => {
  const conversations = ref<Conversation[]>([])
  const currentConversationId = ref<string>('')
  const loading = ref(false)

  const currentConversation = computed(() => {
    return conversations.value.find(c => c.id === currentConversationId.value)
  })

  const createConversation = () => {
    const conversation: Conversation = {
      id: Date.now().toString(),
      title: '新对话',
      messages: [],
      createdAt: Date.now()
    }
    conversations.value.unshift(conversation)
    currentConversationId.value = conversation.id
    return conversation
  }

  const addMessage = (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => {
    const conversation = conversations.value.find(c => c.id === conversationId)
    if (conversation) {
      const newMessage: Message = {
        ...message,
        id: Date.now().toString(),
        timestamp: Date.now()
      }
      conversation.messages.push(newMessage)
      
      // 更新对话标题
      if (conversation.messages.length === 1 && message.role === 'user') {
        conversation.title = message.content.slice(0, 20) + (message.content.length > 20 ? '...' : '')
      }
    }
  }

  const deleteConversation = (id: string) => {
    const index = conversations.value.findIndex(c => c.id === id)
    if (index > -1) {
      conversations.value.splice(index, 1)
      if (currentConversationId.value === id) {
        currentConversationId.value = conversations.value[0]?.id || ''
      }
    }
  }

  return {
    conversations,
    currentConversationId,
    currentConversation,
    loading,
    createConversation,
    addMessage,
    deleteConversation
  }
})
