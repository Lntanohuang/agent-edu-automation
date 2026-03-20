<template>
  <section class="placeholder app-panel">
    <h2>{{ pageTitle }}</h2>
    <p class="muted">该模块已完成视觉占位，功能将在后续迭代补齐。</p>
    <el-result icon="info" title="规划中" sub-title="已预留路由、权限与布局结构" />
  </section>
</template>

<script setup lang="ts">
defineProps<{
  pageTitle: string;
}>();
</script>

<style scoped>
.placeholder {
  min-height: calc(100vh - 124px);
  padding: 18px;
}

h2 {
  margin: 0;
}

p {
  margin: 8px 0 18px;
}
</style>
