<template>
  <div class="contract-wrap">
    <section class="overview app-panel rise-in">
      <div>
        <h2 class="lux-title">合同审阅工作区</h2>
        <p class="lux-subtitle">逐条识别风险，支持采纳/忽略/备注闭环。</p>
      </div>
      <div class="overview-metrics">
        <article>
          <small>高风险</small>
          <strong>{{ highRiskCount }}</strong>
        </article>
        <article>
          <small>待处理</small>
          <strong>{{ pendingRiskCount }}</strong>
        </article>
        <article>
          <small>已采纳</small>
          <strong>{{ acceptedRiskCount }}</strong>
        </article>
      </div>
    </section>

    <div class="contract-page">
      <section class="clause-pane app-panel rise-in stagger-1">
      <header class="pane-head">
        <h2>合同条款</h2>
        <el-tag type="info">{{ clauses.length }} 条</el-tag>
      </header>
      <div class="contract-name muted">{{ contractName }}</div>
      <div v-loading="loading" class="clause-list soft-scroll">
        <article
          v-for="item in clauses"
          :key="item.id"
          class="clause-card card-hover"
          :class="{ active: item.id === selectedClauseId }"
          @click="selectedClauseId = item.id"
        >
          <strong>{{ item.title }}</strong>
          <p>{{ item.summary }}</p>
        </article>
      </div>
      </section>

      <section class="risk-pane app-panel rise-in stagger-2">
      <header class="pane-head">
        <h2>风险审阅</h2>
        <div class="actions">
          <el-button :disabled="authStore.profile?.role === 'intern'">保存审阅结果</el-button>
          <el-button type="primary" :disabled="authStore.profile?.role === 'intern'">导出审阅报告</el-button>
        </div>
      </header>

      <div class="risk-list soft-scroll">
        <article v-for="risk in clauseRisks" :key="risk.id" class="risk-card card-hover">
          <header>
            <strong>{{ risk.title }}</strong>
            <div class="risk-tags">
              <el-tag :type="riskLevelType(risk.level)" effect="dark">{{ riskLevelLabel(risk.level) }}</el-tag>
              <el-tag :type="riskStatusType(risk.status)" effect="light">{{ riskStatusLabel(risk.status) }}</el-tag>
            </div>
          </header>
          <p>{{ risk.suggestion }}</p>
          <p v-if="risk.remark" class="remark">备注：{{ risk.remark }}</p>
          <footer>
            <el-button
              size="small"
              :disabled="authStore.profile?.role === 'intern'"
              @click="updateRiskStatus(risk.id, 'accepted')"
            >
              采纳
            </el-button>
            <el-button
              size="small"
              :disabled="authStore.profile?.role === 'intern'"
              @click="updateRiskStatus(risk.id, 'ignored')"
            >
              忽略
            </el-button>
            <el-button
              size="small"
              type="primary"
              :disabled="authStore.profile?.role === 'intern'"
              @click="openRemarkDialog(risk.id)"
            >
              备注
            </el-button>
          </footer>
        </article>
      </div>
      </section>
    </div>

    <el-dialog v-model="remarkDialogVisible" title="添加备注" width="420px">
      <el-input v-model="remarkText" type="textarea" :rows="5" placeholder="请输入审阅备注..." />
      <template #footer>
        <el-button @click="remarkDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitRemark">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { useAuthStore } from '@/stores/auth';
import { mockGateway } from '@/services/mockGateway';
import type { ContractClause, ContractRisk } from '@/types';

const authStore = useAuthStore();

const loading = ref(false);
const contractName = ref('');
const clauses = ref<ContractClause[]>([]);
const risks = ref<ContractRisk[]>([]);
const selectedClauseId = ref('');
const remarkDialogVisible = ref(false);
const remarkText = ref('');
const currentRiskId = ref('');

const clauseRisks = computed(() => risks.value.filter((item) => item.clauseId === selectedClauseId.value));
const highRiskCount = computed(() => risks.value.filter((item) => item.level === 'high').length);
const pendingRiskCount = computed(() => risks.value.filter((item) => item.status === 'pending').length);
const acceptedRiskCount = computed(() => risks.value.filter((item) => item.status === 'accepted').length);

function riskLevelType(level: ContractRisk['level']) {
  if (level === 'high') {
    return 'danger';
  }
  if (level === 'medium') {
    return 'warning';
  }
  return 'info';
}

function riskLevelLabel(level: ContractRisk['level']) {
  if (level === 'high') {
    return '高风险';
  }
  if (level === 'medium') {
    return '中风险';
  }
  return '低风险';
}

function riskStatusType(status: ContractRisk['status']) {
  if (status === 'accepted') {
    return 'success';
  }
  if (status === 'ignored') {
    return 'info';
  }
  return 'warning';
}

function riskStatusLabel(status: ContractRisk['status']) {
  if (status === 'accepted') {
    return '已采纳';
  }
  if (status === 'ignored') {
    return '已忽略';
  }
  return '待处理';
}

function updateRiskStatus(riskId: string, status: ContractRisk['status']) {
  if (authStore.profile?.role === 'intern') {
    ElMessage.warning('当前角色无权限修改审阅结论');
    return;
  }
  const index = risks.value.findIndex((item) => item.id === riskId);
  if (index < 0) {
    return;
  }
  const targetRisk = risks.value[index];
  if (!targetRisk) {
    return;
  }
  targetRisk.status = status;
  ElMessage.success(status === 'accepted' ? '已标记为采纳' : '已标记为忽略');
}

function openRemarkDialog(riskId: string) {
  if (authStore.profile?.role === 'intern') {
    ElMessage.warning('当前角色无权限添加备注');
    return;
  }
  currentRiskId.value = riskId;
  remarkText.value = risks.value.find((item) => item.id === riskId)?.remark ?? '';
  remarkDialogVisible.value = true;
}

function submitRemark() {
  if (!currentRiskId.value) {
    return;
  }
  const targetRisk = risks.value.find((item) => item.id === currentRiskId.value);
  if (!targetRisk) {
    return;
  }
  targetRisk.remark = remarkText.value.trim();
  remarkDialogVisible.value = false;
  ElMessage.success('备注已保存');
}

onMounted(async () => {
  loading.value = true;
  const data = await mockGateway.fetchContractReviewData();
  contractName.value = data.contractName;
  clauses.value = data.clauses;
  risks.value = data.risks.map((item) => ({ ...item }));
  const firstClause = clauses.value[0];
  if (firstClause) {
    selectedClauseId.value = firstClause.id;
  }
  loading.value = false;
});
</script>

<style scoped>
.contract-wrap {
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

.overview-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
}

.overview-metrics article {
  min-width: 88px;
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 8px 10px;
  background: var(--bg-soft);
  display: grid;
}

.overview-metrics small {
  color: var(--text-secondary);
  font-size: 12px;
}

.overview-metrics strong {
  font-size: 22px;
  line-height: 1;
}

.contract-page {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 14px;
}

.clause-pane,
.risk-pane {
  min-height: calc(100vh - 124px);
  padding: 16px;
}

.pane-head {
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

.contract-name {
  margin-bottom: 12px;
}

.clause-list {
  display: grid;
  gap: 9px;
  max-height: calc(100vh - 290px);
  overflow: auto;
}

.clause-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 10px;
  background: var(--bg-soft);
  cursor: pointer;
}

.clause-card.active {
  border-color: var(--gold-primary);
  background: var(--gold-soft);
}

.clause-card p {
  margin: 5px 0 0;
  font-size: 13px;
}

.actions {
  display: flex;
  gap: 8px;
}

.risk-list {
  display: grid;
  gap: 9px;
  max-height: calc(100vh - 290px);
  overflow: auto;
}

.risk-card {
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg-soft);
}

.risk-card header {
  display: flex;
  justify-content: space-between;
  gap: 8px;
}

.risk-tags {
  display: flex;
  gap: 6px;
}

.risk-card p {
  margin: 8px 0 0;
}

.remark {
  color: var(--text-secondary);
  font-size: 13px;
}

.risk-card footer {
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

@media (max-width: 1180px) {
  .overview {
    flex-direction: column;
    align-items: flex-start;
  }

  .overview-metrics {
    width: 100%;
  }

  .contract-page {
    grid-template-columns: 1fr;
  }

  .clause-pane,
  .risk-pane {
    min-height: auto;
  }

  .pane-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
