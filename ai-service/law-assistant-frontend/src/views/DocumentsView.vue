<template>
  <div class="documents-page">
    <section class="left-panel app-panel">
      <header class="panel-header">
        <h2>资料库</h2>
        <el-tag type="info">{{ documents.length }} 份</el-tag>
      </header>

      <el-upload
        drag
        :show-file-list="false"
        :auto-upload="false"
        accept=".pdf"
        class="upload-box"
        @change="handleUpload"
      >
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="el-upload__text">拖拽 PDF 或点击上传</div>
        <template #tip>
          <div class="el-upload__tip">当前为 mock 模式：上传后将进入解析队列</div>
        </template>
      </el-upload>

      <div class="task-box">
        <header>
          <h3>任务流水线</h3>
          <el-button text type="primary" @click="refreshTasks">刷新</el-button>
        </header>
        <div v-loading="tasksLoading" class="task-list">
          <article v-for="item in pipelineTasks" :key="item.id" class="task-item">
            <div>
              <strong>{{ item.type }}</strong>
              <p class="muted">{{ item.targetName }}</p>
            </div>
            <el-tag :type="taskStatusType(item.status)" effect="light">{{ taskStatusLabel(item.status) }}</el-tag>
            <el-progress :percentage="item.progress" :stroke-width="6" />
          </article>
        </div>
      </div>
    </section>

    <section class="right-panel app-panel">
      <header class="panel-header">
        <h2>文档清单</h2>
        <div class="header-actions">
          <el-button>批量解析</el-button>
          <el-button type="primary" :disabled="authStore.profile?.role === 'intern'">导出索引</el-button>
        </div>
      </header>

      <el-table v-loading="docsLoading" :data="documents" class="docs-table">
        <el-table-column prop="title" label="文档" min-width="260" />
        <el-table-column prop="caseName" label="所属案件" min-width="180" />
        <el-table-column prop="pages" label="页数" width="90" />
        <el-table-column prop="uploader" label="上传人" width="110" />
        <el-table-column prop="updatedAt" label="更新时间" width="170" />
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="docStatusType(row.status)" effect="light">{{ docStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary">查看</el-button>
            <el-button text :disabled="authStore.profile?.role === 'intern' || row.status !== 'ready'">
              导出
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { UploadFilled } from '@element-plus/icons-vue';
import type { UploadFile } from 'element-plus';
import { ElMessage } from 'element-plus';
import { mockGateway } from '@/services/mockGateway';
import { useAuthStore } from '@/stores/auth';
import type { DocumentItem, TaskItem } from '@/types';

const authStore = useAuthStore();
const docsLoading = ref(false);
const tasksLoading = ref(false);
const documents = ref<DocumentItem[]>([]);
const pipelineTasks = ref<TaskItem[]>([]);

function docStatusType(status: DocumentItem['status']) {
  if (status === 'ready') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  if (status === 'processing') {
    return 'warning';
  }
  return 'info';
}

function docStatusLabel(status: DocumentItem['status']) {
  if (status === 'ready') {
    return '已入库';
  }
  if (status === 'failed') {
    return '失败';
  }
  if (status === 'processing') {
    return '处理中';
  }
  return '待处理';
}

function taskStatusType(status: TaskItem['status']) {
  if (status === 'success') {
    return 'success';
  }
  if (status === 'failed') {
    return 'danger';
  }
  if (status === 'processing') {
    return 'warning';
  }
  return 'info';
}

function taskStatusLabel(status: TaskItem['status']) {
  if (status === 'success') {
    return '完成';
  }
  if (status === 'failed') {
    return '失败';
  }
  if (status === 'processing') {
    return '执行中';
  }
  return '队列中';
}

async function refreshDocuments() {
  docsLoading.value = true;
  documents.value = await mockGateway.fetchDocuments();
  docsLoading.value = false;
}

async function refreshTasks() {
  tasksLoading.value = true;
  pipelineTasks.value = await mockGateway.fetchPipelineTasks();
  tasksLoading.value = false;
}

function handleUpload(file: UploadFile) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    ElMessage.warning('当前仅支持 PDF 文件');
    return;
  }
  ElMessage.success(`已加入解析队列：${file.name}`);
  documents.value.unshift({
    id: `doc-${Date.now()}`,
    title: file.name,
    caseName: '未归档案件',
    pages: 0,
    uploader: authStore.profile?.name ?? '当前用户',
    updatedAt: new Date().toLocaleString(),
    status: 'pending'
  });
}

onMounted(async () => {
  await Promise.all([refreshDocuments(), refreshTasks()]);
});
</script>

<style scoped>
.documents-page {
  display: grid;
  grid-template-columns: 380px minmax(0, 1fr);
  gap: 14px;
}

.left-panel,
.right-panel {
  padding: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

h2 {
  margin: 0;
  font-size: 21px;
}

.upload-box {
  border-radius: 12px;
  overflow: hidden;
}

.upload-box :deep(.el-upload-dragger) {
  background: var(--bg-soft);
  border-color: var(--border-color);
  min-height: 170px;
}

.upload-icon {
  color: var(--gold-primary);
}

.task-box {
  margin-top: 16px;
}

.task-box header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-list {
  margin-top: 8px;
  display: grid;
  gap: 8px;
}

.task-item {
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  padding: 10px;
}

.task-item p {
  margin: 2px 0 8px;
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.docs-table :deep(.el-table__inner-wrapper::before) {
  background-color: transparent;
}

@media (max-width: 1180px) {
  .documents-page {
    grid-template-columns: 1fr;
  }
}
</style>
