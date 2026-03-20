<template>
  <el-button-group>
    <el-tooltip content="亮色模式" placement="bottom">
      <el-button :type="themeMode === 'light' ? 'primary' : 'default'" @click="setTheme('light')">
        <el-icon><Sunny /></el-icon>
      </el-button>
    </el-tooltip>
    <el-tooltip content="暗色模式" placement="bottom">
      <el-button :type="themeMode === 'dark' ? 'primary' : 'default'" @click="setTheme('dark')">
        <el-icon><Moon /></el-icon>
      </el-button>
    </el-tooltip>
  </el-button-group>
</template>

<script setup lang="ts">
import { storeToRefs } from 'pinia';
import { Moon, Sunny } from '@element-plus/icons-vue';
import { useUiStore, type ThemeMode } from '@/stores/ui';

const uiStore = useUiStore();
const { themeMode } = storeToRefs(uiStore);

function setTheme(mode: ThemeMode) {
  uiStore.setTheme(mode);
}
</script>
