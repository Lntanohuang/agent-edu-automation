<template>
  <div class="intelligent-qa page-view">
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
                <div v-if="message.role === 'assistant' && message.confidence"
                     class="message-meta">
                  <el-tag :type="confidenceType(message.confidence)" size="small">
                    {{ confidenceLabel(message.confidence) }}
                  </el-tag>
                  <el-tag v-if="message.skillUsed" type="info" size="small">
                    {{ message.skillUsed }}
                  </el-tag>
                </div>
                <el-collapse v-if="message.sources && message.sources.length > 0" class="sources-collapse">
                  <el-collapse-item title="查看来源">
                    <ul class="sources-list">
                      <li v-for="src in message.sources" :key="src">{{ src }}</li>
                    </ul>
                  </el-collapse-item>
                </el-collapse>
                <div class="feedback-row" v-if="message.role === 'assistant'">
                  <span class="feedback-label">这个回答</span>
                  <el-button
                    text
                    size="small"
                    :type="feedbackState[message.id] === 'helpful' ? 'success' : ''"
                    @click="submitFeedback(message, 'helpful')">
                    👍 有用
                  </el-button>
                  <el-button
                    text
                    size="small"
                    :type="feedbackState[message.id] === 'not_helpful' ? 'danger' : ''"
                    @click="submitFeedback(message, 'not_helpful')">
                    👎 无用
                  </el-button>
                </div>
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
import type { Message } from '../stores/chat'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ragFeedbackApi, type FeedbackPayload } from '../api/index'
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
const feedbackState = ref<Record<string, string>>({})

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

const confidenceType = (c: string): '' | 'success' | 'warning' | 'danger' | 'info' =>
  c === 'high' ? 'success' : c === 'medium' ? 'warning' : 'danger'

const confidenceLabel = (c: string): string =>
  ({ high: '高置信度', medium: '中等置信度', low: '低置信度' } as Record<string, string>)[c] ?? c

const submitFeedback = async (message: Message, rating: 'helpful' | 'not_helpful') => {
  if (feedbackState.value[message.id]) return
  feedbackState.value[message.id] = rating
  try {
    const payload: FeedbackPayload = {
      conversation_id: currentConversation.value?.id ?? '',
      message_id: message.id,
      rating,
      confidence: message.confidence,
    }
    await ragFeedbackApi.submit(payload)
    ElMessage.success('感谢您的反馈！')
  } catch {
    ElMessage.error('提交反馈失败')
    delete feedbackState.value[message.id]
  }
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
  min-height: calc(100vh - 154px);

  .qa-container {
    display: flex;
    min-height: inherit;
    border: 1px solid var(--border-color);
    border-radius: 16px;
    background: var(--surface-1);
    box-shadow: var(--shadow-xs);
    overflow: hidden;

    .sidebar {
      width: 270px;
      background: var(--surface-2);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;

      .sidebar-header {
        padding: 14px;
        border-bottom: 1px solid var(--border-color);

        .new-chat-btn {
          width: 100%;
        }
      }

      .conversation-list {
        flex: 1;

        .conversation-item {
          display: flex;
          align-items: center;
          gap: 10px;
          margin: 6px 10px;
          padding: 10px 12px;
          border: 1px solid transparent;
          border-radius: 10px;
          color: var(--text-secondary);
          cursor: pointer;
          transition: all 0.2s ease;

          &:hover {
            border-color: var(--border-color);
            background: var(--surface-1);

            .delete-btn {
              opacity: 1;
            }
          }

          &.active {
            border-color: color-mix(in srgb, var(--color-accent) 50%, var(--border-color));
            background: color-mix(in srgb, var(--color-accent) 14%, var(--surface-1));
            color: var(--text-primary);
          }

          .title {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 13px;
            font-weight: 520;
            color: var(--text-primary);
          }

          .delete-btn {
            opacity: 0;
            transition: opacity 0.2s ease;
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
            color: var(--text-primary);
          }

          p {
            color: var(--text-secondary);
            margin-bottom: 24px;
          }

          .quick-questions {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            max-width: 600px;

            .quick-tag {
              cursor: pointer;
              padding: 8px 14px;
              font-size: 13px;
              border-radius: 999px;
              background: var(--surface-1);
              border-color: var(--border-color);
              color: var(--text-primary);

              &:hover {
                border-color: var(--color-accent);
                color: var(--color-accent);
              }
            }
          }
        }
      }

      .chat-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 18px;
        border-bottom: 1px solid var(--border-color);
        background: var(--surface-1);

        .chat-title {
          font-size: 16px;
          font-weight: 620;
          color: var(--text-primary);
        }

        .chat-actions {
          display: flex;
          gap: 8px;
        }
      }

      .message-list {
        flex: 1;
        padding: 18px 18px 12px;
        background: color-mix(in srgb, var(--bg-canvas) 92%, var(--surface-1));

        .message-item {
          display: flex;
          gap: 12px;
          margin-bottom: 18px;

          &.user {
            flex-direction: row-reverse;

            .message-content {
              align-items: flex-end;
            }

            .message-bubble {
              background: linear-gradient(150deg, var(--color-primary), var(--color-primary-hover));
              color: var(--text-on-primary);
              border-color: transparent;
            }
          }

          .message-avatar {
            .el-avatar {
              &.user {
                background: var(--color-primary);
              }

              &.assistant {
                background: var(--surface-3);
                color: var(--text-primary);
              }
            }
          }

          .message-content {
            display: flex;
            flex-direction: column;
            gap: 4px;
            max-width: 70%;

            .message-bubble {
              padding: 10px 14px;
              background: var(--surface-1);
              border: 1px solid var(--border-color);
              border-radius: 12px;
              box-shadow: var(--shadow-xs);
              line-height: 1.6;
              color: var(--text-primary);

              :deep(.empty-message-hint) {
                margin: 0;
                color: var(--text-tertiary);
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
                  background: var(--text-tertiary);
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

              :deep(ul),
              :deep(ol) {
                margin: 8px 0;
                padding-left: 20px;
              }

              :deep(code) {
                background: var(--surface-2);
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
                color: var(--text-primary);
              }

              :deep(pre) {
                background: var(--surface-2);
                padding: 12px;
                border-radius: 4px;
                overflow-x: auto;

                code {
                  background: none;
                  padding: 0;
                  color: var(--text-primary);
                }
              }

              :deep(a) {
                color: var(--color-accent);
              }
            }

            .message-time {
              font-size: 12px;
              color: var(--text-tertiary);
            }

            .message-meta {
              display: flex;
              gap: 6px;
              flex-wrap: wrap;
              margin-top: 4px;
            }

            .sources-collapse {
              margin-top: 6px;
              font-size: 13px;
            }

            .sources-list {
              padding-left: 18px;
              margin: 4px 0;

              li {
                margin: 2px 0;
              }
            }

            .feedback-row {
              display: flex;
              align-items: center;
              gap: 6px;
              margin-top: 6px;
              padding-top: 6px;
              border-top: 1px solid var(--border-color);

              .feedback-label {
                font-size: 12px;
                color: var(--text-tertiary);
              }
            }
          }
        }
      }

      .input-area {
        padding: 14px 18px;
        border-top: 1px solid var(--border-color);
        background: var(--surface-1);

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
