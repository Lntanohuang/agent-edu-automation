<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside width="240px" class="sidebar">
      <div class="logo">
        <el-icon size="32" color="#409EFF"><School /></el-icon>
        <span class="title">智能教育平台</span>
      </div>
      
      <el-menu
        :default-active="$route.path"
        router
        class="menu"
        background-color="#001529"
        text-color="#fff"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        
        <el-menu-item index="/qa">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        
        <el-menu-item index="/lesson-plan">
          <el-icon><Document /></el-icon>
          <span>智能教案生成</span>
        </el-menu-item>

        <el-menu-item index="/rag">
          <el-icon><FolderOpened /></el-icon>
          <span>RAG 知识库</span>
        </el-menu-item>
      </el-menu>
      
      <div class="sidebar-footer">
        <el-button type="primary" :icon="Setting" text>系统设置</el-button>
      </div>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container class="main-container">
      <el-header class="header">
        <div class="header-left">
          <breadcrumb />
        </div>
        <div class="header-right">
          <el-badge :value="3" class="message-badge">
            <el-icon size="20"><Bell /></el-icon>
          </el-badge>
          <el-dropdown>
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">教师</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item>个人中心</el-dropdown-item>
                <el-dropdown-item>修改密码</el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'
import {
  HomeFilled,
  ChatDotRound,
  Document,
  FolderOpened,
  Bell,
  UserFilled,
  ArrowDown,
  School,
  Setting
} from '@element-plus/icons-vue'

const router = useRouter()

const handleLogout = async () => {
  try {
    await authApi.logout()
  } catch (_error) {
    // 忽略后端退出失败，本地登录态仍需清理
  } finally {
    localStorage.removeItem('token')
    localStorage.removeItem('refreshToken')
    ElMessage.success('已退出登录')
    await router.replace('/login')
  }
}
</script>

<style scoped lang="scss">
.main-layout {
  height: 100vh;
  
  .sidebar {
    background: #001529;
    display: flex;
    flex-direction: column;
    
    .logo {
      height: 64px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 0 16px;
      border-bottom: 1px solid rgba(255,255,255,0.1);
      
      .title {
        color: #fff;
        font-size: 18px;
        font-weight: 600;
        margin-left: 12px;
      }
    }
    
    .menu {
      flex: 1;
      border-right: none;
      
      :deep(.el-menu-item) {
        height: 50px;
        line-height: 50px;
        
        &:hover {
          background: #1890ff !important;
        }
        
        &.is-active {
          background: #1890ff !important;
        }
      }
    }
    
    .sidebar-footer {
      padding: 16px;
      border-top: 1px solid rgba(255,255,255,0.1);
      
      .el-button {
        color: #fff;
        width: 100%;
      }
    }
  }
  
  .main-container {
    background: #f0f2f5;
    
    .header {
      background: #fff;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 1px 4px rgba(0,21,41,0.08);
      
      .header-right {
        display: flex;
        align-items: center;
        gap: 24px;
        
        .message-badge {
          cursor: pointer;
        }
        
        .user-info {
          display: flex;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          
          .username {
            font-size: 14px;
            color: #333;
          }
        }
      }
    }
    
    .main-content {
      padding: 20px;
      overflow-y: auto;
    }
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
