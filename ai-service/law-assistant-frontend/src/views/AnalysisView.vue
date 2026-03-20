<template>
  <div class="analysis-page">
    <section class="filter-row app-panel rise-in">
      <div class="left">
        <h2 class="lux-title">类案 / 庭审</h2>
        <el-select v-model="selectedCaseId" placeholder="选择案件" style="width: 320px">
          <el-option v-for="item in cases" :key="item.id" :label="item.name" :value="item.id" />
        </el-select>
      </div>
      <div class="right">
        <el-button>刷新分析</el-button>
        <el-button type="primary" :disabled="authStore.profile?.role === 'intern'">生成庭审提纲</el-button>
      </div>
    </section>

    <section class="metrics-row">
      <article class="metric-card app-panel rise-in stagger-1">
        <p class="muted">类案数量</p>
        <strong>{{ similarCases.length }}</strong>
      </article>
      <article class="metric-card app-panel rise-in stagger-2">
        <p class="muted">平均支持率</p>
        <strong>{{ avgSupportRate }}%</strong>
      </article>
      <article class="metric-card app-panel rise-in stagger-3">
        <p class="muted">庭审待办</p>
        <strong>{{ pendingPointsCount }}</strong>
      </article>
    </section>

    <section class="content-panel app-panel rise-in stagger-4">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="类案分析" name="cases">
          <div v-loading="loading" class="case-grid soft-scroll">
            <article v-for="item in similarCases" :key="item.id" class="case-card card-hover">
              <header>
                <strong>{{ item.title }}</strong>
                <el-tag type="warning" effect="plain">{{ item.supportRate }}%</el-tag>
              </header>
              <p class="muted">{{ item.court }} · {{ item.cause }}</p>
              <p>{{ item.focus }}</p>
              <el-progress :percentage="item.supportRate" :stroke-width="6" />
            </article>
          </div>
        </el-tab-pane>
        <el-tab-pane label="庭审要点" name="hearing">
          <div v-loading="loading" class="hearing-list soft-scroll">
            <article v-for="point in hearingPoints" :key="point.id" class="hearing-card card-hover">
              <div class="head">
                <el-checkbox :model-value="point.done" @change="togglePoint(point.id, $event)" />
                <strong>{{ point.title }}</strong>
                <el-tag :type="categoryType(point.category)" effect="light">{{ point.category }}</el-tag>
              </div>
              <p>{{ point.detail }}</p>
            </article>
          </div>
        </el-tab-pane>
      </el-tabs>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { mockGateway } from '@/services/mockGateway';
import type { CaseItem, HearingPoint, SimilarCaseItem } from '@/types';

const authStore = useAuthStore();

const loading = ref(false);
const activeTab = ref('cases');
const selectedCaseId = ref('');
const cases = ref<CaseItem[]>([]);
const similarCases = ref<SimilarCaseItem[]>([]);
const hearingPoints = ref<HearingPoint[]>([]);
const avgSupportRate = computed(() => {
  if (similarCases.value.length === 0) {
    return 0;
  }
  const total = similarCases.value.reduce((sum, item) => sum + item.supportRate, 0);
  return Math.round(total / similarCases.value.length);
});
const pendingPointsCount = computed(() => hearingPoints.value.filter((item) => !item.done).length);

function categoryType(category: HearingPoint['category']) {
  if (category === '争点') {
    return 'danger';
  }
  if (category === '举证') {
    return 'warning';
  }
  return 'success';
}

function togglePoint(pointId: string, value: string | number | boolean) {
  const item = hearingPoints.value.find((point) => point.id === pointId);
  if (!item) {
    return;
  }
  item.done = Boolean(value);
}

onMounted(async () => {
  loading.value = true;
  const [caseData, analysisData] = await Promise.all([
    mockGateway.fetchCases(),
    mockGateway.fetchAnalysisData()
  ]);
  cases.value = caseData;
  const firstCase = cases.value[0];
  if (firstCase) {
    selectedCaseId.value = firstCase.id;
  }
  similarCases.value = analysisData.similarCases;
  hearingPoints.value = analysisData.hearingPoints.map((item) => ({ ...item }));
  loading.value = false;
});
</script>

<style scoped>
.analysis-page {
  display: grid;
  gap: 14px;
}

.filter-row {
  padding: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.left,
.right {
  display: flex;
  align-items: center;
  gap: 10px;
}

h2 {
  margin: 0;
}

.metrics-row {
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

.content-panel {
  padding: 16px;
  min-height: calc(100vh - 206px);
}

.case-grid,
.hearing-list {
  display: grid;
  gap: 10px;
  max-height: calc(100vh - 320px);
  overflow: auto;
}

.case-card,
.hearing-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg-soft);
}

.case-card header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.case-card p {
  margin: 6px 0;
}

.head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.hearing-card p {
  margin: 8px 0 0;
  padding-left: 28px;
}

@media (max-width: 1024px) {
  .metrics-row {
    grid-template-columns: 1fr;
  }

  .filter-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .left,
  .right {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
