<template>
  <div class="shell">
    <aside class="shell-side app-panel rise-in" :class="{ collapsed: uiStore.sidebarCollapsed }">
      <div class="brand-row">
        <div class="brand-mark">律</div>
        <div v-if="!uiStore.sidebarCollapsed" class="brand-text">
          <strong>法律助手</strong>
          <span>Lawyer Workspace</span>
        </div>
      </div>
      <el-menu
        class="side-menu"
        :default-active="activeMenu"
        :collapse="uiStore.sidebarCollapsed"
        router
        unique-opened
      >
        <el-menu-item v-for="item in menuItems" :key="item.path" :index="menuPath(item.path)">
          <el-icon v-if="item.meta?.icon">
            <component :is="iconMap[item.meta.icon] ?? Menu" />
          </el-icon>
          <span>{{ item.meta?.title }}</span>
        </el-menu-item>
      </el-menu>
      <div class="side-footer muted" v-if="!uiStore.sidebarCollapsed">
        当前租户：{{ authStore.profile?.tenantName }}
      </div>
    </aside>

    <section class="shell-main">
      <header class="topbar app-panel rise-in stagger-1">
        <div class="topbar-left">
          <el-button text @click="uiStore.toggleSidebar()">
            <el-icon><Fold v-if="!uiStore.sidebarCollapsed" /><Expand v-else /></el-icon>
          </el-button>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>法律助手</el-breadcrumb-item>
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.meta?.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="topbar-right">
          <ThemeToggle />
          <el-tag class="role-tag" type="warning" effect="dark">{{ authStore.roleLabel }}</el-tag>
          <el-tag v-if="!uiStore.sidebarCollapsed" class="tenant-tag" effect="plain">
            {{ authStore.profile?.tenantName }}
          </el-tag>
          <el-dropdown trigger="click">
            <span class="user-entry">
              {{ authStore.profile?.name }}
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="content-wrap">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue';
import { useRoute, useRouter, type RouteRecordRaw } from 'vue-router';
import {
  ArrowDown,
  ChatLineRound,
  Clock,
  DataLine,
  Document,
  Expand,
  Files,
  Fold,
  FolderOpened,
  Menu,
  Reading,
  Setting
} from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import { useUiStore } from '@/stores/ui';
import ThemeToggle from '@/components/ThemeToggle.vue';

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const uiStore = useUiStore();

const iconMap: Record<string, Component> = {
  DataLine,
  FolderOpened,
  ChatLineRound,
  Document,
  Reading,
  Files,
  Clock,
  Setting
};

const rootRoute = router.options.routes.find((item) => item.path === '/');
const childRoutes = (rootRoute?.children ?? []) as RouteRecordRaw[];

const menuItems = computed(() =>
  childRoutes.filter((item) => !item.meta?.hidden && authStore.hasRole(item.meta?.roles))
);

const activeMenu = computed(() => route.path);
const breadcrumbs = computed(() => route.matched.filter((item) => item.meta?.title && item.path !== '/'));

function menuPath(path: string) {
  return path.startsWith('/') ? path : `/${path}`;
}

function logout() {
  authStore.logout();
  router.replace('/login');
}
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  min-height: 100vh;
  padding: 14px;
}

.shell-side {
  width: 240px;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--gold-soft), transparent 10%), transparent 30%),
    var(--bg-elevated);
  backdrop-filter: blur(6px);
  transition: width 0.24s ease;
}

.shell-side.collapsed {
  width: 84px;
}

.brand-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 2px 8px 16px;
  border-bottom: 1px solid color-mix(in srgb, var(--border-color), var(--gold-primary) 12%);
  margin-bottom: 6px;
}

.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #f7f3eb;
  background: linear-gradient(130deg, var(--gold-primary), #5f4a22);
  font-weight: 600;
}

.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
  gap: 2px;
}

.brand-text strong {
  font-size: 14px;
}

.brand-text span {
  font-size: 11px;
  color: var(--text-secondary);
}

.side-menu {
  flex: 1;
  border: none;
  background: transparent;
}

.side-menu :deep(.el-menu-item) {
  border-radius: 10px;
  margin-bottom: 6px;
  min-height: 42px;
  transition: all var(--duration-fast) ease;
}

.side-menu :deep(.el-menu-item:hover) {
  background: var(--gold-soft);
}

.side-menu :deep(.el-menu-item.is-active) {
  background: linear-gradient(90deg, var(--gold-soft), transparent);
  color: var(--gold-strong);
  font-weight: 600;
}

.side-footer {
  border-top: 1px dashed var(--border-color);
  margin: 10px 8px 2px;
  padding-top: 12px;
  font-size: 12px;
}

.shell-main {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 14px;
  min-width: 0;
}

.topbar {
  min-height: 64px;
  padding: 10px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 14px;
  z-index: 10;
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.role-tag {
  border: none;
  font-weight: 500;
}

.tenant-tag {
  border-color: var(--border-color);
  color: var(--text-secondary);
}

.user-entry {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: var(--text-primary);
}

.content-wrap {
  min-width: 0;
  padding-bottom: 8px;
}

@media (max-width: 1024px) {
  .shell {
    grid-template-columns: 1fr;
  }

  .shell-side {
    width: 100%;
  }

  .shell-side.collapsed {
    width: 100%;
  }
}
</style>
