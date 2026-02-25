import { createRouter, createWebHistory } from 'vue-router';
import type { UserRole } from '@/types';
import { useAuthStore } from '@/stores/auth';
import LoginView from '@/views/LoginView.vue';
import WorkbenchView from '@/views/WorkbenchView.vue';
import DocumentsView from '@/views/DocumentsView.vue';
import AssistantView from '@/views/AssistantView.vue';
import DraftsView from '@/views/DraftsView.vue';
import ContractReviewView from '@/views/ContractReviewView.vue';
import AnalysisView from '@/views/AnalysisView.vue';
import TasksCenterView from '@/views/TasksCenterView.vue';
import SettingsView from '@/views/SettingsView.vue';
import MainLayout from '@/layouts/MainLayout.vue';

declare module 'vue-router' {
  interface RouteMeta {
    title?: string;
    icon?: string;
    requiresAuth?: boolean;
    roles?: UserRole[];
    hidden?: boolean;
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: {
        title: '登录',
        hidden: true
      }
    },
    {
      path: '/',
      component: MainLayout,
      redirect: '/workbench',
      meta: {
        requiresAuth: true
      },
      children: [
        {
          path: 'workbench',
          name: 'workbench',
          component: WorkbenchView,
          meta: {
            title: '案件工作台',
            icon: 'DataLine'
          }
        },
        {
          path: 'documents',
          name: 'documents',
          component: DocumentsView,
          meta: {
            title: '资料库',
            icon: 'FolderOpened'
          }
        },
        {
          path: 'assistant',
          name: 'assistant',
          component: AssistantView,
          meta: {
            title: '检索问答',
            icon: 'ChatLineRound'
          }
        },
        {
          path: 'drafts',
          name: 'drafts',
          component: DraftsView,
          meta: {
            title: '文书',
            icon: 'Document'
          }
        },
        {
          path: 'contract-review',
          name: 'contract-review',
          component: ContractReviewView,
          meta: {
            title: '合同审阅',
            icon: 'Reading'
          }
        },
        {
          path: 'analysis',
          name: 'analysis',
          component: AnalysisView,
          meta: {
            title: '类案/庭审',
            icon: 'Files'
          }
        },
        {
          path: 'tasks',
          name: 'tasks',
          component: TasksCenterView,
          meta: {
            title: '任务中心',
            icon: 'Clock'
          }
        },
        {
          path: 'settings',
          name: 'settings',
          component: SettingsView,
          meta: {
            title: '系统管理',
            icon: 'Setting',
            roles: ['partner']
          }
        }
      ]
    }
  ]
});

router.beforeEach((to) => {
  const authStore = useAuthStore();
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return {
      path: '/login',
      query: {
        redirect: to.fullPath
      }
    };
  }

  if (to.meta.roles && to.meta.roles.length > 0 && !authStore.hasRole(to.meta.roles)) {
    return '/workbench';
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return '/workbench';
  }

  return true;
});

export default router;
