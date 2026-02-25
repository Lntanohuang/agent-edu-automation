<template>
  <div class="dashboard page-view">
    <!-- 欢迎区域 -->
    <div class="welcome-section">
      <div class="welcome-text">
        <h1>欢迎回来，{{ displayName }}！</h1>
        <p>今天是 {{ today }}，开启您的智能教学之旅</p>
      </div>
      <div class="quick-actions">
        <el-button type="primary" size="large" @click="$router.push('/qa')">
          <el-icon class="el-icon--left"><ChatDotRound /></el-icon>
          开始智能问答
        </el-button>
        <el-button size="large" @click="$router.push('/lesson-plan')">
          <el-icon class="el-icon--left"><Document /></el-icon>
          生成教案
        </el-button>
      </div>
    </div>
    
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6" v-for="stat in statistics" :key="stat.title">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ background: stat.color }">
              <el-icon size="32" color="#fff"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 功能模块 -->
    <el-row :gutter="20" class="features-row">
      <el-col :span="12" v-for="feature in features" :key="feature.title">
        <el-card class="feature-card" shadow="hover" @click="$router.push(feature.route)">
          <div class="feature-content">
            <div class="feature-icon" :style="{ background: feature.bgColor }">
              <el-icon size="40"><component :is="feature.icon" /></el-icon>
            </div>
            <h3>{{ feature.title }}</h3>
            <p>{{ feature.description }}</p>
            <el-button type="primary" text>
              立即使用 <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 最近活动和快捷入口 -->
    <el-row :gutter="20" class="bottom-row">
      <el-col :span="12">
        <el-card class="activity-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>最近活动</span>
              <el-button type="primary" text>查看全部</el-button>
            </div>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(activity, index) in recentActivities"
              :key="index"
              :type="activity.type"
              :timestamp="activity.time"
            >
              {{ activity.content }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
      
      <el-col :span="12">
        <el-card class="notice-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span>系统公告</span>
              <el-button type="primary" text>更多</el-button>
            </div>
          </template>
          <el-scrollbar height="280px">
            <div class="notice-list">
              <div v-for="(notice, index) in notices" :key="index" class="notice-item">
                <el-tag :type="notice.type" size="small">{{ notice.tag }}</el-tag>
                <span class="notice-title">{{ notice.title }}</span>
                <span class="notice-time">{{ notice.time }}</span>
              </div>
            </div>
          </el-scrollbar>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue'
import {
  ChatDotRound,
  ChatLineRound,
  DocumentChecked,
  Document,
  FolderOpened,
  Collection,
  ArrowRight
} from '@element-plus/icons-vue'
import { authApi, chatApi, ragAiApi, type ConversationData, type SpringPage } from '../api'
import { useLessonPlanStore } from '../stores/lessonPlan'

interface StatItem {
  title: string
  value: string | number
  icon: Component
  color: string
}

interface ActivityItem {
  content: string
  time: string
  type: 'primary' | 'success' | 'warning' | 'info' | 'danger'
  timestamp: number
}

interface NoticeItem {
  title: string
  tag: string
  type: 'primary' | 'success' | 'warning' | 'info' | 'danger'
  time: string
}

interface ConversationListFallback {
  list: ConversationData[]
  total: number
  page: number
  size: number
}

const lessonPlanStore = useLessonPlanStore()
const displayName = ref('教师')
const conversations = ref<ConversationData[]>([])
const totalConversationCount = ref(0)
const ragBookCount = ref<number | null>(null)
const backendOnline = ref(false)
const ragOnline = ref(false)

const today = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
})

const formatDate = (timestamp: number) => {
  return new Date(timestamp).toLocaleDateString('zh-CN')
}

const formatRelativeTime = (timestamp: number) => {
  const diffMs = Date.now() - timestamp
  if (diffMs < 60_000) return '刚刚'
  if (diffMs < 3_600_000) return `${Math.floor(diffMs / 60_000)}分钟前`
  if (diffMs < 86_400_000) return `${Math.floor(diffMs / 3_600_000)}小时前`
  return formatDate(timestamp)
}

const parseTime = (value?: string): number => {
  if (!value) return Date.now()
  const parsed = Date.parse(value)
  return Number.isNaN(parsed) ? Date.now() : parsed
}

const extractConversationData = (
  payload: SpringPage<ConversationData> | ConversationListFallback
): { list: ConversationData[]; total: number } => {
  if ('content' in payload) {
    return {
      list: payload.content || [],
      total: payload.totalElements ?? (payload.content || []).length
    }
  }
  return {
    list: payload.list || [],
    total: payload.total ?? (payload.list || []).length
  }
}

const totalMessageCount = computed(() =>
  conversations.value.reduce((sum, item) => sum + Number(item.messageCount || 0), 0)
)

const statistics = computed<StatItem[]>(() => [
  { title: '问答消息', value: totalMessageCount.value, icon: ChatLineRound, color: '#2b3037' },
  { title: '生成教案', value: lessonPlanStore.lessonPlans.length, icon: DocumentChecked, color: '#8a6b3f' },
  { title: '活跃对话', value: totalConversationCount.value, icon: FolderOpened, color: '#5f6876' },
  { title: '知识库资料', value: ragBookCount.value ?? 0, icon: Collection, color: '#8e949f' }
])

const features = [
  {
    title: '智能问答',
    description: '基于大语言模型的智能教学助手，随时解答教学相关问题',
    icon: ChatDotRound,
    bgColor: 'linear-gradient(140deg, #2b3037 0%, #424a55 100%)',
    route: '/qa'
  },
  {
    title: '智能教案生成',
    description: '根据教学需求自动生成完整教案，支持多种格式导出',
    icon: Document,
    bgColor: 'linear-gradient(140deg, #7c6238 0%, #b38b54 100%)',
    route: '/lesson-plan'
  }
]

const recentActivities = computed<ActivityItem[]>(() => {
  const fromConversation: ActivityItem[] = conversations.value.map((item) => ({
    content: `进行了「${item.title || '新对话'}」问答`,
    time: formatRelativeTime(parseTime(item.updatedAt || item.createdAt)),
    type: 'primary',
    timestamp: parseTime(item.updatedAt || item.createdAt)
  }))

  const fromLessonPlans: ActivityItem[] = lessonPlanStore.lessonPlans.map((item) => ({
    content: `生成了《${item.title}》教案`,
    time: formatRelativeTime(item.createdAt),
    type: 'success',
    timestamp: item.createdAt
  }))

  const merged = [...fromLessonPlans, ...fromConversation]
    .sort((a, b) => b.timestamp - a.timestamp)
    .slice(0, 4)

  if (merged.length > 0) return merged
  return [
    {
      content: '暂无活动记录，去创建第一条教学内容吧',
      time: '刚刚',
      type: 'info',
      timestamp: Date.now()
    }
  ]
})

const notices = computed<NoticeItem[]>(() => {
  const now = formatDate(Date.now())
  return [
    {
      title: backendOnline.value ? '后端服务连接正常' : '后端服务暂不可用，请检查 8080 服务',
      tag: backendOnline.value ? '状态' : '告警',
      type: backendOnline.value ? 'success' : 'warning',
      time: now
    },
    {
      title: ragOnline.value
        ? `知识库已索引 ${ragBookCount.value ?? 0} 本资料`
        : '知识库服务暂不可用，请检查 8000 服务',
      tag: ragOnline.value ? '资源' : '告警',
      type: ragOnline.value ? 'info' : 'warning',
      time: now
    },
    {
      title: `当前账号：${displayName.value}`,
      tag: '账号',
      type: 'primary',
      time: now
    },
    {
      title: `近 50 条对话消息总数：${totalMessageCount.value}`,
      tag: '统计',
      type: 'success',
      time: now
    }
  ]
})

const loadDashboardData = async () => {
  try {
    const me = await authApi.getCurrentUser()
    displayName.value = me.data.nickname || me.data.username || '教师'
    backendOnline.value = true
  } catch (error) {
    console.warn('获取用户信息失败', error)
  }

  try {
    const conversationResponse = await chatApi.getConversations(1, 50)
    const normalized = extractConversationData(
      conversationResponse.data || { content: [], totalElements: 0, number: 0, size: 50 }
    )
    conversations.value = normalized.list
    totalConversationCount.value = normalized.total
    backendOnline.value = true
  } catch (error) {
    console.warn('获取对话统计失败', error)
  }

  try {
    const books = await ragAiApi.listBooks()
    ragBookCount.value = Number(books.total || 0)
    ragOnline.value = true
  } catch (error) {
    console.warn('获取知识库统计失败', error)
  }
}

onMounted(() => {
  void loadDashboardData()
})
</script>

<style scoped lang="scss">
.dashboard {
  gap: 18px;

  .welcome-section {
    border: 1px solid var(--border-color);
    border-radius: 18px;
    padding: 26px 28px;
    color: var(--text-on-primary);
    background: linear-gradient(150deg, var(--color-primary), var(--color-primary-hover));
    box-shadow: var(--shadow-sm);
    display: flex;
    justify-content: space-between;
    align-items: center;

    .welcome-text {
      h1 {
        font-size: 30px;
        font-weight: 650;
        line-height: 1.25;
        margin-bottom: 8px;
      }

      p {
        font-size: 14px;
        opacity: 0.86;
      }
    }

    .quick-actions {
      display: flex;
      gap: 10px;
    }
  }

  .stats-row {
    .stat-card {
      border-radius: 14px;

      .stat-content {
        display: flex;
        align-items: center;
        gap: 14px;

        .stat-icon {
          width: 54px;
          height: 54px;
          border-radius: 14px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: inset 0 0 0 1px color-mix(in srgb, #ffffff 18%, transparent);
        }

        .stat-info {
          .stat-value {
            font-size: 26px;
            font-weight: 650;
            line-height: 1.1;
            color: var(--text-primary);
          }

          .stat-title {
            font-size: 14px;
            color: var(--text-secondary);
            margin-top: 4px;
          }
        }
      }
    }
  }

  .features-row {
    .feature-card {
      border-radius: 14px;
      cursor: pointer;
      transition: transform 0.2s ease, box-shadow 0.2s ease;

      &:hover {
        transform: translateY(-2px);
        box-shadow: var(--shadow-sm);
      }

      .feature-content {
        padding: 10px 4px;

        .feature-icon {
          width: 58px;
          height: 58px;
          border-radius: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-bottom: 16px;
          color: #fff;
        }

        h3 {
          margin: 0;
          font-size: 19px;
          color: var(--text-primary);
        }

        p {
          margin: 10px 0 12px;
          font-size: 14px;
          color: var(--text-secondary);
          line-height: 1.7;
          min-height: 44px;
        }

        :deep(.el-button) {
          color: var(--color-accent);
        }
      }
    }
  }

  .bottom-row {
    min-height: 350px;

    .activity-card,
    .notice-card {
      height: 350px;

      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 620;
        color: var(--text-primary);
      }
    }

    .notice-list {
      .notice-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px dashed var(--border-color);

        &:last-child {
          border-bottom: none;
        }

        .notice-title {
          flex: 1;
          font-size: 14px;
          color: var(--text-primary);
        }

        .notice-time {
          font-size: 12px;
          color: var(--text-tertiary);
        }
      }
    }
  }
}
</style>
