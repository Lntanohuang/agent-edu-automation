<template>
  <el-container class="main-layout">
    <el-aside width="252px" class="sidebar">
      <div class="brand">
        <div class="brand-mark">
          <el-icon size="20"><School /></el-icon>
        </div>
        <div class="brand-text">
          <p class="brand-title">智能教育平台</p>
          <p class="brand-subtitle">Legal Teaching Workspace</p>
        </div>
      </div>

      <el-menu :default-active="route.path" router class="nav-menu">
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="item.path">
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </el-menu-item>
      </el-menu>

      <div class="sidebar-footer">
        <el-button text :icon="Setting">系统设置</el-button>
      </div>
    </el-aside>

    <el-container class="workspace">
      <el-header class="workspace-header">
        <div class="header-main">
          <h1 class="page-title">{{ pageTitle }}</h1>
          <el-breadcrumb separator="/" class="page-breadcrumb">
            <el-breadcrumb-item
              v-for="item in breadcrumbItems"
              :key="item.path"
              :to="item.path === route.path ? undefined : item.path"
            >
              {{ item.label }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="header-actions">
          <div class="theme-switch">
            <span class="theme-label">亮</span>
            <el-switch v-model="isDark" />
            <span class="theme-label">暗</span>
          </div>

          <el-badge is-dot class="message-badge">
            <el-button circle text :icon="Bell" />
          </el-badge>

          <el-dropdown>
            <span class="user-entry">
              <el-avatar :size="30" :icon="UserFilled" />
              <span class="username">{{ displayName }}</span>
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

      <div class="workspace-body">
        <el-main class="workspace-main">
          <router-view v-slot="{ Component }">
            <transition name="fade" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </el-main>
      </div>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch, type Component } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { authApi } from '../api'
import {
  HomeFilled,
  ChatDotRound,
  Document,
  FolderOpened,
  EditPen,
  Bell,
  UserFilled,
  ArrowDown,
  School,
  Setting
} from '@element-plus/icons-vue'

interface MenuItem {
  path: string
  label: string
  icon: Component
}

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'ui-theme-mode'

const router = useRouter()
const route = useRoute()

const menuItems: MenuItem[] = [
  { path: '/dashboard', label: '首页', icon: HomeFilled },
  { path: '/qa', label: '智能问答', icon: ChatDotRound },
  { path: '/lesson-plan', label: '智能教案生成', icon: Document },
  { path: '/rag', label: 'RAG 知识库', icon: FolderOpened },
  { path: '/question-generator', label: '智能出题', icon: EditPen }
]

const displayName = ref('教师')
const themeMode = ref<ThemeMode>(localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light')

const pageTitle = computed(() => {
  return (route.meta.title as string) || '工作台'
})

const breadcrumbItems = computed(() => {
  const base = [{ path: '/dashboard', label: '工作台' }]
  if (route.path !== '/dashboard') {
    base.push({ path: route.path, label: pageTitle.value })
  }
  return base
})

const isDark = computed({
  get: () => themeMode.value === 'dark',
  set: (value: boolean) => {
    themeMode.value = value ? 'dark' : 'light'
  }
})

const applyTheme = (mode: ThemeMode) => {
  document.documentElement.setAttribute('data-theme', mode)
  localStorage.setItem(THEME_KEY, mode)
}

const loadProfile = async () => {
  try {
    const result = await authApi.getCurrentUser()
    displayName.value = result.data.nickname || result.data.username || '教师'
  } catch (_error) {
    displayName.value = '教师'
  }
}

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

watch(
  themeMode,
  (mode) => {
    applyTheme(mode)
  },
  { immediate: true }
)

onMounted(() => {
  void loadProfile()
})
</script>

<style scoped lang="scss">
.main-layout {
  min-height: 100vh;
  background: transparent;
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 16px 14px;
  border-right: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface-1) 86%, var(--bg-canvas));
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 56px;
  padding: 6px 10px;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  color: var(--text-on-primary);
  background: linear-gradient(150deg, var(--color-primary), var(--color-primary-hover));
}

.brand-text {
  min-width: 0;
}

.brand-title {
  margin: 0;
  font-size: 16px;
  font-weight: 650;
  color: var(--text-primary);
}

.brand-subtitle {
  margin: 3px 0 0;
  font-size: 11px;
  letter-spacing: 0.02em;
  text-transform: uppercase;
  color: var(--text-tertiary);
}

.nav-menu {
  flex: 1;
  background: transparent;
}

:deep(.nav-menu .el-menu-item) {
  margin-bottom: 6px;
  height: 42px;
  border-radius: 10px;
  color: var(--text-secondary);
}

:deep(.nav-menu .el-menu-item:hover) {
  color: var(--text-primary);
  background: var(--surface-2);
}

:deep(.nav-menu .el-menu-item.is-active) {
  color: var(--text-on-primary);
  background: linear-gradient(140deg, var(--color-primary), var(--color-primary-hover));
}

.sidebar-footer {
  padding: 4px;
  border-top: 1px solid var(--border-color);
}

:deep(.sidebar-footer .el-button) {
  width: 100%;
  justify-content: flex-start;
  color: var(--text-secondary);
}

.workspace {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.workspace-header {
  height: 76px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  border-bottom: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface-1) 88%, var(--bg-canvas));
}

.header-main {
  min-width: 0;
}

.page-title {
  margin: 0;
  font-size: 22px;
  line-height: 1.2;
  color: var(--text-primary);
}

.page-breadcrumb {
  margin-top: 6px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.theme-switch {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border: 1px solid var(--border-color);
  border-radius: 999px;
  background: var(--surface-1);
}

.theme-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.message-badge {
  display: inline-flex;
}

.user-entry {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  cursor: pointer;
}

.username {
  font-size: 13px;
  color: var(--text-primary);
}

.workspace-body {
  flex: 1;
  min-height: 0;
  display: block;
  padding: 16px 20px 20px;
}

.workspace-main {
  min-width: 0;
  height: 100%;
  overflow: auto;
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--bg-canvas);
}
</style>
