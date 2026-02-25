<template>
  <div class="tasks-page">
    <section class="headline app-panel rise-in">
      <div>
        <h2 class="lux-title">任务中心</h2>
        <p class="lux-subtitle">统一追踪文档入库、问答评测、文书导出与合同审阅任务。</p>
      </div>
      <el-segmented
        v-model="quickFilter"
        :options="[
          { label: '全部', value: 'all' },
          { label: '执行中', value: 'processing' },
          { label: '阻塞', value: 'blocked' }
        ]"
      />
    </section>

    <section class="summary-grid">
      <article class="summary-card app-panel rise-in stagger-1 card-hover">
        <p class="muted">执行中</p>
        <strong>{{ processingCount }}</strong>
      </article>
      <article class="summary-card app-panel rise-in stagger-2 card-hover">
        <p class="muted">阻塞中</p>
        <strong>{{ blockedCount }}</strong>
      </article>
      <article class="summary-card app-panel rise-in stagger-3 card-hover">
        <p class="muted">已完成</p>
        <strong>{{ successCount }}</strong>
      </article>
    </section>

    <section class="board app-panel rise-in stagger-4">
      <header class="board-head">
        <h2>任务中心</h2>
        <div class="filters">
          <el-select v-model="moduleFilter" clearable placeholder="模块筛选" style="width: 160px">
            <el-option v-for="name in moduleOptions" :key="name" :label="name" :value="name" />
          </el-select>
          <el-select v-model="statusFilter" clearable placeholder="状态筛选" style="width: 160px">
            <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </div>
      </header>
      <el-table v-loading="loading" :data="filteredTasks">
        <el-table-column prop="module" label="模块" width="120" />
        <el-table-column prop="title" label="任务内容" min-width="260" />
        <el-table-column prop="owner" label="负责人" width="100" />
        <el-table-column label="优先级" width="100">
          <template #default="{ row }">
            <el-tag :type="priorityType(row.priority)" effect="light">{{ priorityLabel(row.priority) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="light">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" width="170">
          <template #default="{ row }">
            <el-progress :percentage="row.progress" :stroke-width="6" />
          </template>
        </el-table-column>
        <el-table-column prop="updatedAt" label="更新时间" width="170" />
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary">详情</el-button>
            <el-button
              text
              :disabled="
                authStore.profile?.role === 'intern' || (row.status !== 'failed' && row.status !== 'blocked')
              "
            >
              重试
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { mockGateway } from '@/services/mockGateway';
import type { TaskCenterItem } from '@/types';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();
const loading = ref(false);
const tasks = ref<TaskCenterItem[]>([]);
const moduleFilter = ref('');
const statusFilter = ref('');
const quickFilter = ref<'all' | 'processing' | 'blocked'>('all');

const moduleOptions = computed(() => Array.from(new Set(tasks.value.map((item) => item.module))));
const statusOptions: Array<{ label: string; value: TaskCenterItem['status'] }> = [
  { label: '队列中', value: 'queued' },
  { label: '执行中', value: 'processing' },
  { label: '阻塞中', value: 'blocked' },
  { label: '已完成', value: 'success' },
  { label: '失败', value: 'failed' }
];

const filteredTasks = computed(() =>
  tasks.value.filter((item) => {
    const matchesQuickFilter = quickFilter.value === 'all' ? true : item.status === quickFilter.value;
    const matchesModule = moduleFilter.value ? item.module === moduleFilter.value : true;
    const matchesStatus = statusFilter.value ? item.status === statusFilter.value : true;
    return matchesQuickFilter && matchesModule && matchesStatus;
  })
);

const processingCount = computed(() => tasks.value.filter((item) => item.status === 'processing').length);
const blockedCount = computed(() => tasks.value.filter((item) => item.status === 'blocked').length);
const successCount = computed(() => tasks.value.filter((item) => item.status === 'success').length);

function priorityType(priority: TaskCenterItem['priority']) {
  if (priority === 'high') {
    return 'danger';
  }
  if (priority === 'medium') {
    return 'warning';
  }
  return 'success';
}

function priorityLabel(priority: TaskCenterItem['priority']) {
  if (priority === 'high') {
    return '高';
  }
  if (priority === 'medium') {
    return '中';
  }
  return '低';
}

function statusType(status: TaskCenterItem['status']) {
  if (status === 'success') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  if (status === 'blocked') {
    return 'warning';
  }
  if (status === 'processing') {
    return 'primary';
  }
  return 'info';
}

function statusLabel(status: TaskCenterItem['status']) {
  if (status === 'success') {
    return '已完成';
  }
  if (status === 'failed') {
    return '失败';
  }
  if (status === 'blocked') {
    return '阻塞中';
  }
  if (status === 'processing') {
    return '执行中';
  }
  return '队列中';
}

onMounted(async () => {
  loading.value = true;
  tasks.value = await mockGateway.fetchTaskCenterData();
  loading.value = false;
});
</script>

<style scoped>
.tasks-page {
  display: grid;
  gap: 14px;
}

.headline {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.summary-card {
  padding: 14px 16px;
}

.summary-card p {
  margin: 0 0 6px;
}

.summary-card strong {
  font-size: 28px;
  line-height: 1;
}

.board {
  padding: 16px;
}

.board-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 10px;
}

h2 {
  margin: 0;
  font-size: 21px;
}

.filters {
  display: flex;
  gap: 8px;
}

@media (max-width: 1024px) {
  .headline {
    flex-direction: column;
    align-items: flex-start;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .board-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .filters {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
