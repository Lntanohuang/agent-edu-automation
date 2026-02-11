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
import { ref, computed, nextTick, watch } from 'vue'
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
  html: true,
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

const selectConversation = (id: string) => {
  chatStore.currentConversationId = id
}

const deleteConversation = (id: string) => {
  ElMessageBox.confirm('确定删除该对话吗？', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    chatStore.deleteConversation(id)
    ElMessage.success('删除成功')
  })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return
  
  if (!currentConversation.value) {
    chatStore.createConversation()
  }
  
  const message = inputMessage.value
  inputMessage.value = ''
  
  // 添加用户消息
  chatStore.addMessage(chatStore.currentConversationId, {
    role: 'user',
    content: message
  })
  
  // 模拟 AI 回复
  loading.value = true
  await scrollToBottom()
  
  setTimeout(() => {
    const responses = [
      '这是一个很好的教学问题！我建议您可以从以下几个方面考虑：\n\n1. **明确教学目标** - 确保学生理解核心概念\n2. **设计互动环节** - 增加学生参与度\n3. **使用多媒体资源** - 丰富教学内容\n4. **及时反馈** - 帮助学生巩固知识',
      '根据您的需求，我为您提供以下建议：\n\n- 采用**启发式教学**方法\n- 设计**分层教学**活动\n- 运用**项目式学习**模式\n- 结合**翻转课堂**理念\n\n这些方法可以有效提升教学效果。',
      '我理解您的困惑。针对这个问题，您可以尝试：\n\n### 1. 课前准备\n- 深入了解学生学情\n- 准备充足的教学素材\n\n### 2. 课堂实施\n- 创设真实情境\n- 引导自主探究\n\n### 3. 课后反思\n- 收集学生反馈\n- 持续改进教学'
    ]
    
    const randomResponse = responses[Math.floor(Math.random() * responses.length)]
    
    chatStore.addMessage(chatStore.currentConversationId, {
      role: 'assistant',
      content: randomResponse
    })
    
    loading.value = false
    scrollToBottom()
  }, 1500)
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
  if (currentConversation.value) {
    currentConversation.value.messages = []
  }
}

const renderMarkdown = (content: string) => {
  return md.render(content)
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

// 初始化创建一个对话
if (chatStore.conversations.length === 0) {
  chatStore.createConversation()
}
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
