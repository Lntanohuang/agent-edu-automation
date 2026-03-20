<template>
  <div class="drafts-wrap">
    <section class="overview app-panel rise-in">
      <div>
        <h2 class="lux-title">文书工作区</h2>
        <p class="lux-subtitle">模板化生成、草稿复核、一键导出在同一视图完成。</p>
      </div>
      <div class="overview-stats">
        <article>
          <small>模板</small>
          <strong>{{ templates.length }}</strong>
        </article>
        <article>
          <small>草稿</small>
          <strong>{{ drafts.length }}</strong>
        </article>
      </div>
    </section>

    <div class="drafts-page">
      <section class="left-pane app-panel rise-in stagger-1">
      <header class="section-head">
        <h2>文书模板</h2>
        <el-button text type="primary" @click="refreshData">刷新</el-button>
      </header>
      <div v-loading="loading" class="template-list soft-scroll">
        <article
          v-for="item in templates"
          :key="item.id"
          class="template-card card-hover"
          :class="{ active: item.id === activeTemplateId }"
          @click="activeTemplateId = item.id"
        >
          <strong>{{ item.name }}</strong>
          <p>{{ item.description }}</p>
          <small class="muted">最近使用：{{ item.lastUsedAt }}</small>
        </article>
      </div>
      <el-button type="primary" class="new-btn" @click="createDraftByTemplate">一键生成草稿</el-button>
      </section>

      <section class="middle-pane app-panel rise-in stagger-2">
      <header class="section-head">
        <h2>草稿列表</h2>
        <el-tag type="info">{{ drafts.length }} 份</el-tag>
      </header>
      <div v-loading="loading" class="draft-list soft-scroll">
        <article
          v-for="item in drafts"
          :key="item.id"
          class="draft-row card-hover"
          :class="{ active: item.id === selectedDraftId }"
          @click="selectDraft(item.id)"
        >
          <div>
            <strong>{{ item.title }}</strong>
            <p class="muted">{{ item.caseName }} · {{ item.templateName }}</p>
          </div>
          <div class="row-right">
            <el-tag :type="draftStatusType(item.status)" effect="light">{{ draftStatusLabel(item.status) }}</el-tag>
            <small class="muted">{{ item.updatedAt }}</small>
          </div>
        </article>
      </div>
      </section>

      <section class="right-pane app-panel rise-in stagger-3">
      <header class="section-head">
        <h2>文书编辑</h2>
        <div class="actions">
          <el-button @click="saveDraft">保存</el-button>
          <el-button type="primary" :disabled="authStore.profile?.role === 'intern'">一键导出 Word</el-button>
        </div>
      </header>
      <el-input
        v-model="editorContent"
        type="textarea"
        resize="none"
        :rows="20"
        placeholder="请选择草稿或通过模板生成草稿。"
      />
      <div class="editor-foot muted">当前模式：Mock 编辑器（后续可替换为富文本编辑器）</div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import type { DraftItem, DraftTemplate } from '@/types';
import { useAuthStore } from '@/stores/auth';
import { mockGateway } from '@/services/mockGateway';

const authStore = useAuthStore();
const loading = ref(false);
const templates = ref<DraftTemplate[]>([]);
const drafts = ref<DraftItem[]>([]);
const activeTemplateId = ref('');
const selectedDraftId = ref('');
const editorContent = ref('');

const activeTemplate = computed(() => templates.value.find((item) => item.id === activeTemplateId.value));
const selectedDraft = computed(() => drafts.value.find((item) => item.id === selectedDraftId.value));

function draftStatusType(status: DraftItem['status']) {
  if (status === 'final') {
    return 'success';
  }
  if (status === 'reviewing') {
    return 'warning';
  }
  return 'info';
}

function draftStatusLabel(status: DraftItem['status']) {
  if (status === 'final') {
    return '定稿';
  }
  if (status === 'reviewing') {
    return '复核中';
  }
  return '草稿';
}

function selectDraft(id: string) {
  selectedDraftId.value = id;
  const found = drafts.value.find((item) => item.id === id);
  editorContent.value = found?.content ?? '';
}

function createDraftByTemplate() {
  if (!activeTemplate.value) {
    ElMessage.warning('请先选择模板');
    return;
  }
  const createdDraft: DraftItem = {
    id: `dr-${Date.now()}`,
    title: `${activeTemplate.value.name}（新草稿）`,
    caseName: '华晨设备买卖合同纠纷',
    templateName: activeTemplate.value.name,
    updatedAt: new Date().toLocaleString(),
    status: 'draft',
    content: `${activeTemplate.value.name}\n\n一、诉讼请求\n二、事实与理由\n三、证据目录`
  };
  drafts.value.unshift(createdDraft);
  selectDraft(createdDraft.id);
  ElMessage.success('已基于模板生成草稿');
}

function saveDraft() {
  if (!selectedDraft.value) {
    ElMessage.warning('请先选择草稿');
    return;
  }
  selectedDraft.value.content = editorContent.value;
  selectedDraft.value.updatedAt = new Date().toLocaleString();
  ElMessage.success('草稿已保存');
}

async function refreshData() {
  loading.value = true;
  const workspace = await mockGateway.fetchDraftWorkspaceData();
  templates.value = workspace.templates;
  drafts.value = workspace.drafts.map((item) => ({ ...item }));
  const firstTemplate = templates.value[0];
  if (firstTemplate) {
    activeTemplateId.value = firstTemplate.id;
  }
  const firstDraft = drafts.value[0];
  if (firstDraft) {
    selectDraft(firstDraft.id);
  }
  loading.value = false;
}

onMounted(refreshData);
</script>

<style scoped>
.drafts-wrap {
  display: grid;
  gap: 14px;
}

.overview {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.overview-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.overview-stats article {
  min-width: 90px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  background: var(--bg-soft);
  padding: 8px 10px;
  display: grid;
}

.overview-stats small {
  color: var(--text-secondary);
  font-size: 12px;
}

.overview-stats strong {
  font-size: 22px;
  line-height: 1;
}

.drafts-page {
  display: grid;
  grid-template-columns: 320px 380px minmax(0, 1fr);
  gap: 14px;
}

.left-pane,
.middle-pane,
.right-pane {
  padding: 16px;
  min-height: calc(100vh - 124px);
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  gap: 8px;
}

h2 {
  margin: 0;
  font-size: 21px;
}

.template-list,
.draft-list {
  display: grid;
  gap: 9px;
  max-height: calc(100vh - 280px);
  overflow: auto;
}

.template-card,
.draft-row {
  border: 1px solid var(--border-color);
  border-radius: 11px;
  padding: 10px;
  background: var(--bg-soft);
  cursor: pointer;
}

.template-card.active,
.draft-row.active {
  border-color: var(--gold-primary);
  background: var(--gold-soft);
}

.template-card p,
.draft-row p {
  margin: 4px 0;
  font-size: 12px;
}

.new-btn {
  margin-top: 12px;
  width: 100%;
}

.draft-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.row-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
}

.actions {
  display: flex;
  gap: 8px;
}

.right-pane :deep(.el-textarea__inner) {
  font-family: var(--font-body);
  min-height: calc(100vh - 260px);
}

.editor-foot {
  margin-top: 8px;
  font-size: 12px;
}

@media (max-width: 1280px) {
  .overview {
    flex-direction: column;
    align-items: flex-start;
  }

  .drafts-page {
    grid-template-columns: 1fr;
  }

  .left-pane,
  .middle-pane,
  .right-pane {
    min-height: auto;
  }
}
</style>
