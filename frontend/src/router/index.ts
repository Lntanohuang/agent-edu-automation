import { createRouter, createWebHistory } from 'vue-router'
import Layout from '../layouts/MainLayout.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
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
          path: 'lesson-plan',
          name: 'LessonPlanGenerator',
          component: () => import('../views/LessonPlanGenerator.vue'),
          meta: { title: '智能教案生成', icon: 'Document' }
        },
        {
          path: 'grading',
          name: 'IntelligentGrading',
          component: () => import('../views/IntelligentGrading.vue'),
          meta: { title: '智能报告批阅', icon: 'EditPen' }
        }
      ]
    }
  ]
})

export default router
