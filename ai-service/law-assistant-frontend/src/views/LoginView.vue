<template>
  <div class="login-page">
    <div class="login-card app-panel">
      <h1>法律助手</h1>
      <p class="muted">多律所协同 · 引用可追溯 · 文书可导出</p>

      <section class="role-chooser">
        <p>选择登录角色</p>
        <div class="role-grid">
          <button
            v-for="item in roleOptions"
            :key="item.value"
            class="role-item"
            :class="{ active: role === item.value }"
            @click="role = item.value"
          >
            <strong>{{ item.label }}</strong>
            <span>{{ item.desc }}</span>
          </button>
        </div>
      </section>

      <el-button type="primary" class="submit-btn" size="large" :loading="submitting" @click="login">
        进入案件工作台
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import type { UserRole } from '@/types';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();
const submitting = ref(false);
const role = ref<UserRole>('lawyer');

const roleOptions: Array<{ value: UserRole; label: string; desc: string }> = [
  {
    value: 'partner',
    label: '合伙人',
    desc: '可访问系统管理与全部导出'
  },
  {
    value: 'lawyer',
    label: '律师',
    desc: '可执行案件检索、文书与审阅'
  },
  {
    value: 'intern',
    label: '实习生',
    desc: '可查看与整理，不可导出'
  }
];

async function login() {
  submitting.value = true;
  authStore.loginWithRole(role.value);
  const redirectPath = typeof route.query.redirect === 'string' ? route.query.redirect : '/workbench';
  await router.replace(redirectPath);
  submitting.value = false;
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  padding: 28px;
  display: grid;
  place-items: center;
}

.login-card {
  width: min(520px, 100%);
  padding: 34px;
  background:
    linear-gradient(160deg, rgba(138, 107, 47, 0.1), transparent 42%),
    var(--bg-elevated);
}

h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.1;
}

.role-chooser {
  margin-top: 28px;
}

.role-chooser p {
  margin: 0 0 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.role-item {
  appearance: none;
  border: 1px solid var(--border-color);
  background: var(--bg-soft);
  border-radius: 12px;
  min-height: 96px;
  text-align: left;
  padding: 12px;
  color: var(--text-primary);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 6px;
  transition: border-color 0.2s ease, transform 0.2s ease, background 0.2s ease;
}

.role-item:hover {
  transform: translateY(-2px);
  border-color: var(--gold-primary);
}

.role-item span {
  font-size: 12px;
  color: var(--text-secondary);
}

.role-item.active {
  border-color: var(--gold-primary);
  background: var(--gold-soft);
}

.submit-btn {
  margin-top: 24px;
  width: 100%;
}

@media (max-width: 640px) {
  .login-page {
    padding: 12px;
  }

  .role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
