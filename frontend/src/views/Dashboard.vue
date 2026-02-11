<template>
  <div class="dashboard">
    <!-- 欢迎区域 -->
    <div class="welcome-section">
      <div class="welcome-text">
        <h1>欢迎回来，教师！</h1>
        <p>今天是 {{ today }}，开启您的智能教学之旅</p>
      </div>
      <div class="quick-actions">
        <el-button type="primary" size="large" @click="$router.push('/qa')">
          <el-icon class="el-icon--left"><ChatDotRound /></el-icon>
          开始智能问答
        </el-button>
        <el-button type="success" size="large" @click="$router.push('/lesson-plan')">
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
      <el-col :span="8" v-for="feature in features" :key="feature.title">
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
import { computed } from 'vue'
import {
  ChatDotRound,
  Document,
  EditPen,
  ArrowRight
} from '@element-plus/icons-vue'

const today = computed(() => {
  return new Date().toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long'
  })
})

const statistics = [
  { title: '问答次数', value: 128, icon: 'ChatLineRound', color: '#409EFF' },
  { title: '生成教案', value: 36, icon: 'DocumentChecked', color: '#67C23A' },
  { title: '批阅报告', value: 256, icon: 'FolderOpened', color: '#E6A23C' },
  { title: '节省时间', value: '48h', icon: 'TrendCharts', color: '#F56C6C' }
]

const features = [
  {
    title: '智能问答',
    description: '基于大语言模型的智能教学助手，随时解答教学相关问题',
    icon: ChatDotRound,
    bgColor: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    route: '/qa'
  },
  {
    title: '智能教案生成',
    description: '根据教学需求自动生成完整教案，支持多种格式导出',
    icon: Document,
    bgColor: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
    route: '/lesson-plan'
  },
  {
    title: '智能报告批阅',
    description: 'AI 辅助批量批阅学生作业，提供详细反馈和建议',
    icon: EditPen,
    bgColor: 'linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%)',
    route: '/grading'
  }
]

const recentActivities = [
  { content: '生成了《初中数学-一元二次方程》教案', time: '10分钟前', type: 'success' as const },
  { content: '批阅完成高一二班语文作文', time: '30分钟前', type: 'primary' as const },
  { content: '与AI助手讨论了课程设计问题', time: '1小时前', type: 'info' as const },
  { content: '导出了一份PDF格式的教案', time: '2小时前', type: 'warning' as const }
]

const notices = [
  { title: '系统升级完成，新增批量批阅功能', tag: '更新', type: 'success' as const, time: '2024-01-15' },
  { title: '春节假期系统维护通知', tag: '公告', type: 'warning' as const, time: '2024-01-10' },
  { title: '教案模板库新增50+精品模板', tag: '资源', type: 'info' as const, time: '2024-01-08' },
  { title: 'AI 模型升级，回答质量提升', tag: '更新', type: 'success' as const, time: '2024-01-05' }
]
</script>

<style scoped lang="scss">
.dashboard {
  .welcome-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    padding: 32px;
    margin-bottom: 24px;
    color: #fff;
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .welcome-text {
      h1 {
        font-size: 28px;
        margin-bottom: 8px;
      }
      
      p {
        font-size: 16px;
        opacity: 0.9;
      }
    }
    
    .quick-actions {
      display: flex;
      gap: 16px;
    }
  }
  
  .stats-row {
    margin-bottom: 24px;
    
    .stat-card {
      .stat-content {
        display: flex;
        align-items: center;
        gap: 16px;
        
        .stat-icon {
          width: 64px;
          height: 64px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .stat-info {
          .stat-value {
            font-size: 28px;
            font-weight: 700;
            color: #333;
          }
          
          .stat-title {
            font-size: 14px;
            color: #999;
            margin-top: 4px;
          }
        }
      }
    }
  }
  
  .features-row {
    margin-bottom: 24px;
    
    .feature-card {
      cursor: pointer;
      transition: transform 0.3s;
      
      &:hover {
        transform: translateY(-4px);
      }
      
      .feature-content {
        text-align: center;
        padding: 20px;
        
        .feature-icon {
          width: 80px;
          height: 80px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          margin: 0 auto 20px;
          color: #fff;
        }
        
        h3 {
          font-size: 20px;
          margin-bottom: 12px;
          color: #333;
        }
        
        p {
          font-size: 14px;
          color: #666;
          line-height: 1.6;
          margin-bottom: 16px;
          min-height: 44px;
        }
      }
    }
  }
  
  .bottom-row {
    .activity-card,
    .notice-card {
      height: 350px;
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-weight: 600;
      }
    }
    
    .notice-list {
      .notice-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        
        &:last-child {
          border-bottom: none;
        }
        
        .notice-title {
          flex: 1;
          font-size: 14px;
          color: #333;
        }
        
        .notice-time {
          font-size: 12px;
          color: #999;
        }
      }
    }
  }
}
</style>
