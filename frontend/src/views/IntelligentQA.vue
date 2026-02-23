<template>
  <div class="intelligent-qa">
    <div class="qa-container">
      <!-- 左侧对话列表 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <el-button type="primary" :icon="Plus" @click="createNewChat" class="new-chat-btn">
            新建对话
          </el-button>
        </div>
        
        <el-scrollbar class="conversation-list">
          <div
            v-for="conv in chatStore.conversations"
            :key="conv.id"
            class="conversation-item"
            :class="{ active: chatStore.currentConversationId === conv.id }"
            @click="selectConversation(conv.id)"
          >
            <el-icon><ChatDotRound /></el-icon>
            <span class="title">{{ conv.title }}</span>
            <el-button
              type="danger"
              :icon="Delete"
              circle
              size="small"
              class="delete-btn"
              @click.stop="deleteConversation(conv.id)"
            />
          </div>
        </el-scrollbar>
      </div>
      
      <!-- 右侧聊天区域 -->
      <div class="chat-area">
        <div v-if="!currentConversation" class="empty-state">
          <div class="empty-content">
            <el-icon size="64" color="#ccc"><ChatDotRound /></el-icon>
            <h2>开始智能对话</h2>
            <p>基于大语言模型的智能教学助手，随时解答您的教学问题</p>
            <div class="quick-questions">
              <el-tag
                v-for="question in quickQuestions"
                :key="question"
                class="quick-tag"
                @click="sendQuickQuestion(question)"
              >
                {{ question }}
              </el-tag>
            </div>
          </div>
        </div>
        
        <template v-else>
          <div class="chat-header">
            <span class="chat-title">{{ currentConversation.title }}</span>
            <div class="chat-actions">
              <el-button type="primary" text :icon="Share">分享</el-button>
              <el-button type="danger" text :icon="Delete" @click="clearMessages">清空</el-button>
            </div>
          </div>
          
          <el-scrollbar ref="messageContainer" class="message-list">
            <div
              v-for="message in currentConversation.messages"
              :key="message.id"
              class="message-item"
              :class="message.role"
            >
              <div class="message-avatar">
                <el-avatar
                  :size="40"
                  :icon="message.role === 'user' ? UserFilled : Service"
                  :class="message.role"
                />
              </div>
              <div class="message-content">
                <div class="message-bubble" v-html="renderMarkdown(message.content)"></div>
                <span class="message-time">{{ formatTime(message.timestamp) }}</span>
              </div>
            </div>
            
            <div v-if="loading" class="message-item assistant">
              <div class="message-avatar">
                <el-avatar :size="40" :icon="Service" class="assistant" />
              </div>
              <div class="message-content">
                <div class="message-bubble typing">
                  <span class="dot"></span>
                  <span class="dot"></span>
                  <span class="dot"></span>
                </div>
              </div>
            </div>
          </el-scrollbar>
          
          <div class="input-area">
            <div class="input-wrapper">
              <el-input
                v-model="inputMessage"
                type="textarea"
                :rows="3"
                placeholder="输入您的问题，按 Enter 发送，Shift + Enter 换行..."
                @keydown.enter.prevent="handleEnter"
              />
              <div class="input-actions">
                <el-button type="primary" :icon="Microphone" circle />
                <el-button type="primary" :icon="Position" @click="sendMessage" :loading="loading">
                  发送
                </el-button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Delete,
  ChatDotRound,
  UserFilled,
  Service,
  Share,
  Position,
  Microphone
} from '@element-plus/icons-vue'
import MarkdownIt from 'markdown-it'

const chatStore = useChatStore()
const inputMessage = ref('')
const loading = ref(false)
const messageContainer = ref()

const md = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
})

const currentConversation = computed(() => chatStore.currentConversation)

const quickQuestions = [
  '如何设计一堂生动有趣的数学课？',
  '请帮我分析这篇课文的教学重点',
  '如何激发学生的学习兴趣？',
  '课堂管理有哪些有效方法？',
  '如何设计小组合作学习活动？'
]

const createNewChat = () => {
  chatStore.createConversation()
}

const selectConversation = async (id: string) => {
  try {
    loading.value = true
    await chatStore.selectConversation(id)
  } catch (_error) {
    ElMessage.error('加载对话失败')
  } finally {
    loading.value = false
  }
}

const deleteConversation = (id: string) => {
  ElMessageBox.confirm('确定删除该对话吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    chatStore.deleteConversation(id).then(() => {
      ElMessage.success('删除成功')
    }).catch(() => {
      ElMessage.error('删除失败')
    })
  })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  
  if (!currentConversation.value) {
    chatStore.createConversation()
  }
  
  const message = inputMessage.value
  inputMessage.value = ''

  loading.value = true
  await scrollToBottom()

  try {
    await chatStore.sendMessage(message)
  } catch (_error) {
    ElMessage.error('发送失败，请检查后端服务或登录状态')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const sendQuickQuestion = (question: string) => {
  inputMessage.value = question
  sendMessage()
}

const handleEnter = (e: KeyboardEvent) => {
  if (!e.shiftKey) {
    sendMessage()
  }
}

const clearMessages = () => {
  if (!currentConversation.value) return
  chatStore.clearMessages(currentConversation.value.id).then(() => {
    ElMessage.success('清空成功')
  }).catch(() => {
    ElMessage.error('清空失败')
  })
}

onMounted(async () => {
  try {
    loading.value = true
    await chatStore.refreshConversations()
    if (chatStore.conversations.length > 0) {
      await chatStore.selectConversation(chatStore.conversations[0].id)
    } else {
      chatStore.createConversation()
    }
  } catch (_error) {
    ElMessage.error('加载会话失败，请先登录')
    if (chatStore.conversations.length === 0) {
      chatStore.createConversation()
    }
  } finally {
    loading.value = false
  }
})

const renderMarkdown = (content: string) => {
  const normalized = String(content || '').trim()
  if (!normalized) {
    return '<p class="empty-message-hint">（该条消息内容为空，可能由历史异常数据导致）</p>'
  }
  return md.render(normalized)
}

const formatTime = (timestamp: number) => {
  return new Date(timestamp).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

const scrollToBottom = async () => {
  await nextTick()
  if (messageContainer.value) {
    const scrollbar = messageContainer.value.$el.querySelector('.el-scrollbar__wrap')
    if (scrollbar) {
      scrollbar.scrollTop = scrollbar.scrollHeight
    }
  }
}

watch(() => currentConversation.value?.messages.length, scrollToBottom)
</script>

<style scoped lang="scss">
.intelligent-qa {
  height: calc(100vh - 84px);
  
  .qa-container {
    display: flex;
    height: 100%;
    background: #fff;
    border-radius: 8px;
    overflow: hidden;
    
    .sidebar {
      width: 260px;
      background: #f5f7fa;
      border-right: 1px solid #e4e7ed;
      display: flex;
      flex-direction: column;
      
      .sidebar-header {
        padding: 16px;
        border-bottom: 1px solid #e4e7ed;
        
        .new-chat-btn {
          width: 100%;
        }
      }
      
      .conversation-list {
        flex: 1;
        
        .conversation-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 16px;
          cursor: pointer;
          transition: background 0.3s;
          
          &:hover {
            background: #e6f2ff;
            
            .delete-btn {
              opacity: 1;
            }
          }
          
          &.active {
            background: #409eff;
            color: #fff;
          }
          
          .title {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          
          .delete-btn {
            opacity: 0;
            transition: opacity 0.3s;
          }
        }
      }
    }
    
    .chat-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      
      .empty-state {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        
        .empty-content {
          text-align: center;
          
          h2 {
            margin: 24px 0 12px;
            font-size: 24px;
            color: #333;
          }
          
          p {
            color: #999;
            margin-bottom: 32px;
          }
          
          .quick-questions {
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            justify-content: center;
            max-width: 600px;
            
            .quick-tag {
              cursor: pointer;
              padding: 8px 16px;
              font-size: 14px;
              
              &:hover {
                background: #409eff;
                color: #fff;
              }
            }
          }
        }
      }
      
      .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 24px;
        border-bottom: 1px solid #e4e7ed;
        
        .chat-title {
          font-size: 16px;
          font-weight: 600;
        }
        
        .chat-actions {
          display: flex;
          gap: 8px;
        }
      }
      
      .message-list {
        flex: 1;
        padding: 24px;
        background: #fafafa;
        
        .message-item {
          display: flex;
          gap: 16px;
          margin-bottom: 24px;
          
          &.user {
            flex-direction: row-reverse;
            
            .message-content {
              align-items: flex-end;
            }
            
            .message-bubble {
              background: #409eff;
              color: #fff;
            }
          }
          
          .message-avatar {
            .el-avatar {
              &.user {
                background: #409eff;
              }
              
              &.assistant {
                background: #67c23a;
              }
            }
          }
          
          .message-content {
            display: flex;
            flex-direction: column;
            gap: 4px;
            max-width: 70%;
            
            .message-bubble {
              padding: 12px 16px;
              background: #fff;
              border-radius: 8px;
              box-shadow: 0 2px 8px rgba(0,0,0,0.05);
              line-height: 1.6;

              :deep(.empty-message-hint) {
                margin: 0;
                color: #999;
                font-style: italic;
              }
              
              &.typing {
                display: flex;
                gap: 4px;
                align-items: center;
                min-width: 60px;
                
                .dot {
                  width: 8px;
                  height: 8px;
                  background: #999;
                  border-radius: 50%;
                  animation: typing 1.4s infinite;
                  
                  &:nth-child(2) {
                    animation-delay: 0.2s;
                  }
                  
                  &:nth-child(3) {
                    animation-delay: 0.4s;
                  }
                }
              }
              
              :deep(p) {
                margin: 0 0 8px;
                
                &:last-child {
                  margin-bottom: 0;
                }
              }
              
              :deep(ul), :deep(ol) {
                margin: 8px 0;
                padding-left: 20px;
              }
              
              :deep(code) {
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
              }
              
              :deep(pre) {
                background: #f4f4f4;
                padding: 12px;
                border-radius: 4px;
                overflow-x: auto;
                
                code {
                  background: none;
                  padding: 0;
                }
              }
            }
            
            .message-time {
              font-size: 12px;
              color: #999;
            }
          }
        }
      }
      
      .input-area {
        padding: 16px 24px;
        border-top: 1px solid #e4e7ed;
        background: #fff;
        
        .input-wrapper {
          display: flex;
          gap: 12px;
          
          .el-textarea {
            flex: 1;
          }
          
          .input-actions {
            display: flex;
            flex-direction: column;
            gap: 8px;
          }
        }
      }
    }
  }
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}
</style>
