<template>
  <div class="workbench">
    <section class="pane-left app-panel">
      <div class="pane-heading">
        <h2>案件池</h2>
        <el-tag type="warning" effect="plain">{{ filteredCases.length }} 个案件</el-tag>
      </div>
      <el-input v-model="keyword" placeholder="搜索案件名 / 案由" clearable>
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <div v-loading="loading" class="case-list">
        <article
          v-for="item in filteredCases"
          :key="item.id"
          class="case-row"
          :class="{ active: item.id === selectedCaseId }"
          @click="selectedCaseId = item.id"
        >
          <strong>{{ item.name }}</strong>
          <span class="muted">{{ item.cause }} · {{ item.stage }}</span>
          <div class="row-meta">
            <small>{{ item.owner }}</small>
            <small>开庭 {{ item.hearingDate }}</small>
          </div>
          <el-progress :percentage="item.progress" :show-text="false" :stroke-width="6" />
        </article>
      </div>
    </section>

    <section class="pane-right">
      <div class="headline app-panel">
        <div class="headline-main">
          <h2>{{ activeCase?.name }}</h2>
          <p class="muted">最后更新 {{ activeCase?.updatedAt }} · 当前阶段 {{ activeCase?.stage }}</p>
        </div>
        <div class="headline-actions">
          <el-button type="primary">快速检索</el-button>
          <el-button :disabled="authStore.profile?.role === 'intern'">指派任务</el-button>
        </div>
      </div>

      <div class="metrics">
        <article class="metric-card app-panel">
          <p class="muted">案件进度</p>
          <strong>{{ activeCase?.progress }}%</strong>
        </article>
        <article class="metric-card app-panel">
          <p class="muted">风险指数</p>
          <strong>{{ activeCase?.riskScore }}</strong>
        </article>
        <article class="metric-card app-panel">
          <p class="muted">待办数量</p>
          <strong>{{ currentTasks.length }}</strong>
        </article>
      </div>

      <div class="detail-grid">
        <article class="detail-panel app-panel">
          <header>
            <h3>庭审准备要点</h3>
            <el-tag type="warning">重点</el-tag>
          </header>
          <ul>
            <li>围绕付款节点与验收流程，拆分事实争点并提前准备证据链。</li>
            <li>核对合同违约条款是否存在冲突解释，预设法官追问路径。</li>
            <li>准备对方可能提出的免责抗辩反驳材料。</li>
          </ul>
        </article>

        <article class="detail-panel app-panel">
          <header>
            <h3>近期待办</h3>
            <el-tag type="info">{{ currentTasks.length }} 项</el-tag>
          </header>
          <div class="task-list">
            <div v-for="task in currentTasks" :key="task.id" class="task-row">
              <div>
                <strong>{{ task.title }}</strong>
                <p class="muted">{{ task.assignee }} · 截止 {{ task.deadline }}</p>
              </div>
              <el-tag :type="taskTagType(task.priority)" effect="light">{{ priorityLabel(task.priority) }}</el-tag>
            </div>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Search } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';
import { mockGateway } from '@/services/mockGateway';
import type { CaseItem, WorkbenchTask } from '@/types';

const authStore = useAuthStore();

const loading = ref(true);
const keyword = ref('');
const selectedCaseId = ref('');
const caseList = ref<CaseItem[]>([]);
const taskList = ref<WorkbenchTask[]>([]);

const filteredCases = computed(() => {
  if (!keyword.value.trim()) {
    return caseList.value;
  }
  const normalizedKeyword = keyword.value.trim().toLowerCase();
  return caseList.value.filter(
    (item) =>
      item.name.toLowerCase().includes(normalizedKeyword) ||
      item.cause.toLowerCase().includes(normalizedKeyword)
  );
});

const activeCase = computed(() => filteredCases.value.find((item) => item.id === selectedCaseId.value));

const currentTasks = computed(() => taskList.value.filter((task) => task.status !== 'done'));

function taskTagType(priority: WorkbenchTask['priority']) {
  if (priority === 'high') {
    return 'danger';
  }
  if (priority === 'medium') {
    return 'warning';
  }
  return 'success';
}

function priorityLabel(priority: WorkbenchTask['priority']) {
  if (priority === 'high') {
    return '高';
  }
  if (priority === 'medium') {
    return '中';
  }
  return '低';
}

onMounted(async () => {
  loading.value = true;
  const workbenchData = await mockGateway.fetchWorkbenchData();
  caseList.value = workbenchData.cases;
  taskList.value = workbenchData.tasks;
  const firstCase = caseList.value[0];
  if (firstCase) {
    selectedCaseId.value = firstCase.id;
  }
  loading.value = false;
});
</script>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: 340px minmax(0, 1fr);
  gap: 14px;
}

.pane-left {
  padding: 16px;
  min-height: calc(100vh - 124px);
}

.pane-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

h2 {
  margin: 0;
  font-size: 21px;
}

.case-list {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}

.case-row {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 11px;
  background: var(--bg-soft);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.case-row.active {
  border-color: var(--gold-primary);
  background: var(--gold-soft);
}

.row-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
}

.pane-right {
  display: grid;
  gap: 12px;
}

.headline {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.headline-main p {
  margin: 6px 0 0;
}

.headline-actions {
  display: flex;
  gap: 8px;
}

.metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.metric-card {
  padding: 14px 16px;
}

.metric-card p {
  margin: 0 0 6px;
}

.metric-card strong {
  font-size: 28px;
  line-height: 1;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-panel {
  padding: 16px;
}

.detail-panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-panel h3 {
  margin: 0;
  font-size: 16px;
}

.detail-panel ul {
  margin: 10px 0 0;
  padding-left: 18px;
}

.detail-panel li {
  margin-bottom: 7px;
}

.task-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}

.task-row {
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  padding: 9px 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.task-row p {
  margin: 2px 0 0;
  font-size: 12px;
}

@media (max-width: 1180px) {
  .workbench {
    grid-template-columns: 1fr;
  }

  .pane-left {
    min-height: auto;
  }

  .metrics,
  .detail-grid {
    grid-template-columns: 1fr;
  }

  .headline {
    flex-direction: column;
  }
}
</style>
