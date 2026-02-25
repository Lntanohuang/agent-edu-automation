<template>
  <div class="settings-page">
    <section class="org-panel app-panel rise-in">
      <header class="panel-head">
        <h2 class="lux-title">系统管理</h2>
        <el-button type="primary" @click="saveSettings">保存全部配置</el-button>
      </header>
      <p class="lux-subtitle">管理成员角色、系统参数与租户级策略。</p>
      <div class="org-grid">
        <article class="org-card card-hover">
          <p class="muted">律所名称</p>
          <strong>星海律师事务所</strong>
        </article>
        <article class="org-card card-hover">
          <p class="muted">当前成员</p>
          <strong>{{ users.length }} 人</strong>
        </article>
        <article class="org-card card-hover">
          <p class="muted">当前租户版本</p>
          <strong>Professional</strong>
        </article>
      </div>
    </section>

    <section class="users-panel app-panel rise-in stagger-1">
      <header class="panel-head">
        <h3>成员与角色</h3>
      </header>
      <el-table v-loading="loading" :data="users">
        <el-table-column prop="name" label="姓名" min-width="140" />
        <el-table-column prop="team" label="团队" min-width="160" />
        <el-table-column label="角色" width="150">
          <template #default="{ row }">
            <el-select v-model="row.role">
              <el-option label="合伙人" value="partner" />
              <el-option label="律师" value="lawyer" />
              <el-option label="实习生" value="intern" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-switch v-model="row.status" active-value="active" inactive-value="disabled" />
          </template>
        </el-table-column>
      </el-table>
    </section>

    <section class="config-panel app-panel rise-in stagger-2">
      <header class="panel-head">
        <h3>系统参数</h3>
      </header>
      <div v-loading="loading" class="setting-list">
        <article v-for="item in settings" :key="item.id" class="setting-row card-hover">
          <div>
            <strong>{{ item.key }}</strong>
            <p class="muted">{{ item.description }}</p>
          </div>
          <el-input v-model="item.value" />
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import type { SystemSettingItem, SystemUserItem } from '@/types';
import { mockGateway } from '@/services/mockGateway';

const loading = ref(false);
const users = ref<SystemUserItem[]>([]);
const settings = ref<SystemSettingItem[]>([]);

function saveSettings() {
  ElMessage.success('配置已保存（Mock）');
}

onMounted(async () => {
  loading.value = true;
  const [userData, settingData] = await Promise.all([
    mockGateway.fetchSystemUsers(),
    mockGateway.fetchSystemSettings()
  ]);
  users.value = userData.map((item) => ({ ...item }));
  settings.value = settingData.map((item) => ({ ...item }));
  loading.value = false;
});
</script>

<style scoped>
.settings-page {
  display: grid;
  gap: 14px;
}

.org-panel,
.users-panel,
.config-panel {
  padding: 16px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

h2,
h3 {
  margin: 0;
}

h2 {
  font-size: 21px;
}

h3 {
  font-size: 17px;
}

.org-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.org-card {
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  padding: 10px;
  background: var(--bg-soft);
}

.org-card p {
  margin: 0 0 6px;
}

.users-panel :deep(.el-table),
.config-panel {
  overflow: hidden;
}

.setting-list {
  display: grid;
  gap: 8px;
}

.setting-row {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px;
  background: var(--bg-soft);
  display: grid;
  grid-template-columns: minmax(0, 1fr) 280px;
  gap: 12px;
  align-items: center;
}

.setting-row p {
  margin: 4px 0 0;
}

@media (max-width: 1024px) {
  .org-grid {
    grid-template-columns: 1fr;
  }

  .setting-row {
    grid-template-columns: 1fr;
  }
}
</style>
