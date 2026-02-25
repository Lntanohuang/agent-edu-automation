<template>
  <div class="login-page">
    <div class="login-shell">
      <section class="brand-panel">
        <p class="brand-kicker">INTELLIGENT EDUCATION</p>
        <h1>智能教育平台</h1>
        <p class="brand-desc">统一的教研工作台，覆盖问答、教案、知识库与题库全流程。</p>
        <ul class="brand-points">
          <li>黑金/深灰视觉体系，减少视觉噪音</li>
          <li>双栏工作台布局，提升信息效率</li>
          <li>支持手动亮暗主题切换</li>
        </ul>
      </section>

      <el-card class="login-card">
        <div class="title-wrap">
          <h2>账号登录</h2>
          <p>请输入教师账号与密码</p>
        </div>

        <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
          <el-form-item label="账号" prop="username">
            <el-input v-model="form.username" placeholder="请输入账号" clearable />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
          </el-form-item>
          <el-button type="primary" class="login-btn" :loading="loading" @click="handleLogin">
            登录
          </el-button>
        </el-form>

        <div class="hint">默认测试账号：teacher001 / teacher123</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '../api'

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: 'teacher001',
  password: 'teacher123'
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const result = await authApi.login({
      username: form.username,
      password: form.password
    })

    localStorage.setItem('token', result.data.token)
    localStorage.setItem('refreshToken', result.data.refreshToken)
    ElMessage.success('登录成功')

    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/dashboard'
    await router.replace(redirect)
  } catch (_error) {
    // 错误提示由 axios 拦截器统一处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  padding: 24px;
  display: grid;
  place-items: center;
}

.login-shell {
  width: min(1080px, 100%);
  min-height: 620px;
  padding: 20px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 420px;
  gap: 20px;
  border-radius: 24px;
  border: 1px solid var(--border-color);
  background: color-mix(in srgb, var(--surface-1) 82%, var(--bg-canvas));
  box-shadow: var(--shadow-md);
}

.brand-panel {
  padding: 36px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--color-accent) 30%, var(--border-color));
  background: linear-gradient(
    160deg,
    color-mix(in srgb, var(--surface-1) 88%, var(--bg-canvas)),
    color-mix(in srgb, var(--surface-2) 88%, var(--bg-canvas))
  );
}

.brand-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.12em;
  color: var(--color-accent);
}

.brand-panel h1 {
  margin: 10px 0 12px;
  font-size: 34px;
  line-height: 1.2;
  color: var(--text-primary);
}

.brand-desc {
  margin: 0;
  max-width: 520px;
  font-size: 15px;
  line-height: 1.8;
  color: var(--text-secondary);
}

.brand-points {
  margin: 26px 0 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
  color: var(--text-secondary);
}

.brand-points li {
  line-height: 1.6;
}

.login-card {
  align-self: center;
  border-radius: 18px;
}

.title-wrap {
  margin-bottom: 12px;
}

.title-wrap h2 {
  margin: 0;
  font-size: 26px;
  color: var(--text-primary);
}

.title-wrap p {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--text-secondary);
}

.login-btn {
  width: 100%;
  margin-top: 4px;
}

.hint {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 1080px) {
  .login-shell {
    min-height: auto;
    grid-template-columns: minmax(0, 1fr);
  }

  .brand-panel {
    display: none;
  }
}
</style>
