import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import pinia from './stores'
import router from './router'
import { authApi } from './api'

import 'element-plus/dist/index.css'
import './styles/index.scss'

import App from './App.vue'

const THEME_KEY = 'ui-theme-mode'

function setupInitialTheme(): void {
  const savedTheme = localStorage.getItem(THEME_KEY)
  const initialTheme = savedTheme === 'dark' ? 'dark' : 'light'
  document.documentElement.setAttribute('data-theme', initialTheme)
}

const AUTO_LOGIN = import.meta.env.VITE_AUTO_LOGIN === 'true'
const DEFAULT_USERNAME = import.meta.env.VITE_DEFAULT_USERNAME || 'teacher001'
const DEFAULT_PASSWORD = import.meta.env.VITE_DEFAULT_PASSWORD || 'teacher123'

async function ensureAuth(): Promise<void> {
  const token = localStorage.getItem('token')
  if (token || !AUTO_LOGIN) {
    return
  }

  try {
    const result = await authApi.login({
      username: DEFAULT_USERNAME,
      password: DEFAULT_PASSWORD
    })
    localStorage.setItem('token', result.data.token)
    localStorage.setItem('refreshToken', result.data.refreshToken)
  } catch (error) {
    console.error('自动登录失败，请检查后端用户初始化数据', error)
  }
}

async function bootstrap(): Promise<void> {
  setupInitialTheme()
  await ensureAuth()

  const app = createApp(App)

  // 注册所有图标
  for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
  }

  app.use(pinia)
  app.use(router)
  app.use(ElementPlus, { zIndex: 3000 })
  app.mount('#app')
}

void bootstrap()
