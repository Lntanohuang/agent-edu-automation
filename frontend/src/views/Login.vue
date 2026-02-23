<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <div class="title-wrap">
        <h1>智能教育平台</h1>
        <p>请登录后继续使用</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top" @submit.prevent>
        <el-form-item label="账号" prop="username">
          <el-input v-model="form.username" placeholder="请输入账号" clearable />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-button type="primary" style="width: 100%" :loading="loading" @click="handleLogin">
          登录
        </el-button>
      </el-form>

      <div class="hint">默认测试账号：teacher001 / teacher123</div>
    </el-card>
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
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4edf8 100%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 420px;

  .title-wrap {
    text-align: center;
    margin-bottom: 16px;

    h1 {
      font-size: 24px;
      margin-bottom: 8px;
      color: #222;
    }

    p {
      color: #666;
      font-size: 14px;
    }
  }

  .hint {
    margin-top: 12px;
    color: #999;
    font-size: 12px;
    text-align: center;
  }
}
</style>
