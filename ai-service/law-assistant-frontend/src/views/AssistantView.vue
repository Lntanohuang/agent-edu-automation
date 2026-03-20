<template>
  <div class="assistant-page">
    <section class="chat-panel app-panel">
      <header class="chat-head">
        <h2>检索问答</h2>
        <div class="head-actions">
          <el-radio-group v-model="mode" size="small">
            <el-radio-button label="library" :disabled="authStore.profile?.role === 'intern'">
              全库检索
            </el-radio-button>
            <el-radio-button label="case">按案件检索</el-radio-button>
          </el-radio-group>
          <el-select
            v-model="selectedCaseId"
            size="small"
            :disabled="mode !== 'case'"
            placeholder="选择案件"
            style="width: 220px"
          >
            <el-option v-for="item in cases" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </div>
      </header>

      <div ref="messageContainerRef" class="messages">
        <article
          v-for="item in messages"
          :key="item.id"
          class="bubble"
          :class="item.role === 'user' ? 'bubble-user' : 'bubble-assistant'"
        >
          <header>{{ item.role === 'user' ? '你' : '法律助手' }}</header>
          <p>{{ item.content }}</p>
          <small v-if="item.warning" class="warning">{{ item.warning }}</small>
        </article>
      </div>

      <footer class="chat-input">
        <el-input
          v-model="question"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="请输入问题，例如：结合本案合同第 4.2 条，违约责任主张是否充分？"
          @keydown.ctrl.enter.prevent="sendQuestion"
        />
        <div class="input-row">
          <span class="muted">Ctrl + Enter 发送</span>
          <el-button type="primary" :loading="sending" @click="sendQuestion">发送</el-button>
        </div>
      </footer>
    </section>

    <aside class="citation-panel app-panel">
      <header>
        <h3>引用依据</h3>
        <el-tag type="warning" effect="plain">{{ citations.length }} 条</el-tag>
      </header>
      <div class="citation-list">
        <article v-for="item in citations" :key="item.id" class="citation-item">
          <strong>{{ item.sourceTitle }}</strong>
          <div class="meta muted">
            <span>{{ sourceLabel(item.sourceType) }}</span>
            <span>第 {{ item.pageNo }} 页</span>
          </div>
          <p>{{ item.snippet }}</p>
          <el-button text type="primary">打开原文</el-button>
        </article>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import type { CaseItem, CitationItem } from '@/types';
import { mockGateway } from '@/services/mockGateway';
import { useAuthStore } from '@/stores/auth';

interface MessageItem {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  warning?: string;
}

const authStore = useAuthStore();

const mode = ref<'library' | 'case'>('library');
const selectedCaseId = ref('');
const question = ref('');
const sending = ref(false);
const cases = ref<CaseItem[]>([]);
const citations = ref<CitationItem[]>([]);
const messages = ref<MessageItem[]>([
  {
    id: 'msg-welcome',
    role: 'assistant',
    content: '你可以先输入争议焦点，我会给出可追溯引用的分析结论。'
  }
]);
const messageContainerRef = ref<HTMLDivElement | null>(null);

function sourceLabel(type: CitationItem['sourceType']) {
  if (type === 'law') {
    return '法条';
  }
  if (type === 'case') {
    return '案例';
  }
  return '案件材料';
}

function pushMessage(message: MessageItem) {
  messages.value.push(message);
  nextTick(() => {
    if (messageContainerRef.value) {
      messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
    }
  });
}

async function sendQuestion() {
  if (!question.value.trim()) {
    ElMessage.warning('请输入问题后再发送');
    return;
  }

  if (mode.value === 'case' && !selectedCaseId.value) {
    ElMessage.warning('请先选择案件');
    return;
  }

  const text = question.value.trim();
  question.value = '';
  pushMessage({
    id: `user-${Date.now()}`,
    role: 'user',
    content: text
  });

  sending.value = true;
  const reply = await mockGateway.askAssistant({
    question: text,
    mode: mode.value,
    caseId: mode.value === 'case' ? selectedCaseId.value : undefined
  });
  citations.value = reply.citations;
  pushMessage({
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: reply.answer,
    warning: reply.warning
  });
  sending.value = false;
}

onMounted(async () => {
  cases.value = await mockGateway.fetchCases();
  const firstCase = cases.value[0];
  if (firstCase) {
    selectedCaseId.value = firstCase.id;
  }
  if (authStore.profile?.role === 'intern') {
    mode.value = 'case';
  }
});
</script>

<style scoped>
.assistant-page {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 14px;
}

.chat-panel {
  padding: 14px;
  min-height: calc(100vh - 124px);
  display: grid;
  grid-template-rows: auto 1fr auto;
  gap: 12px;
}

.chat-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 21px;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.messages {
  background: var(--bg-soft);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 10px;
  overflow: auto;
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.bubble {
  border-radius: 11px;
  padding: 10px 12px;
  max-width: 80%;
}

.bubble header {
  font-size: 12px;
  margin-bottom: 4px;
  opacity: 0.8;
}

.bubble p {
  margin: 0;
  white-space: pre-wrap;
}

.bubble-user {
  margin-left: auto;
  background: var(--gold-soft);
  border: 1px solid rgba(138, 107, 47, 0.32);
}

.bubble-assistant {
  background: var(--bg-elevated);
  border: 1px solid var(--border-color);
}

.warning {
  display: inline-block;
  margin-top: 8px;
  color: #a76624;
}

.chat-input {
  display: grid;
  gap: 7px;
}

.input-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.citation-panel {
  padding: 14px;
  min-height: calc(100vh - 124px);
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 10px;
}

.citation-panel header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

h3 {
  margin: 0;
  font-size: 18px;
}

.citation-list {
  overflow: auto;
  display: grid;
  gap: 8px;
}

.citation-item {
  border: 1px dashed var(--border-color);
  border-radius: 10px;
  padding: 10px;
}

.citation-item strong {
  display: block;
  margin-bottom: 4px;
}

.citation-item p {
  margin: 8px 0;
  font-size: 13px;
}

.meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}

@media (max-width: 1180px) {
  .assistant-page {
    grid-template-columns: 1fr;
  }

  .chat-panel,
  .citation-panel {
    min-height: auto;
  }

  .chat-head {
    flex-direction: column;
  }

  .head-actions {
    flex-wrap: wrap;
  }
}
</style>
