import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/Login.vue'),
      meta: { public: true }
    },
    {
      path: '/',
      component: Layout,
      redirect: '/dashboard',
      children: [
        {
          path: 'dashboard',
          name: 'Dashboard',
          component: () => import('../views/Dashboard.vue'),
          meta: { title: '首页', icon: 'HomeFilled' }
        },
        {
          path: 'qa',
          name: 'IntelligentQA',
          component: () => import('../views/IntelligentQA.vue'),
          meta: { title: '智能问答', icon: 'ChatDotRound' }
        },
        {
          // /lesson-plan 指向 V2（Multi-Agent Supervisor，自动入库）
          path: 'lesson-plan',
          name: 'LessonPlanGenerator',
          component: () => import('../views/LessonPlanGeneratorV2.vue'),
          meta: { title: '智能教案生成', icon: 'Document' }
        },
        {
          path: 'rag',
          name: 'RagWorkbench',
          component: () => import('../views/RagWorkbench.vue'),
          meta: { title: 'RAG 知识库', icon: 'FolderOpened' }
        },
        {
          // 保留旧 V1 页面作为备份，不在侧边栏展示
          path: 'lesson-plan-v1-legacy',
          name: 'LessonPlanGeneratorV1Legacy',
          component: () => import('../views/LessonPlanGenerator.vue'),
          meta: { title: '教案生成(旧)', hidden: true }
        },
        {
          path: 'question-generator',
          name: 'QuestionGenerator',
          component: () => import('../views/QuestionGenerator.vue'),
          meta: { title: '智能出题', icon: 'EditPen' }
        }
      ]
    }
  ]
})

router.beforeEach((to) => {
  const token = localStorage.getItem('token')
  const isPublicRoute = Boolean(to.meta.public)

  if (!token && !isPublicRoute) {
    return {
      path: '/login',
      query: { redirect: to.fullPath }
    }
  }

  if (token && to.path === '/login') {
    const redirect = typeof to.query.redirect === 'string' ? to.query.redirect : '/dashboard'
    return redirect
  }

  return true
})

export default router
