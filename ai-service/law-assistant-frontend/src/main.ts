import { createApp } from 'vue';
import { createPinia } from 'pinia';
import ElementPlus from 'element-plus';
import zhCn from 'element-plus/es/locale/lang/zh-cn';
import * as ElementPlusIconsVue from '@element-plus/icons-vue';
import App from './App.vue';
import router from './router';
import { useUiStore } from './stores/ui';
import 'element-plus/dist/index.css';
import '@/assets/theme.css';
import '@/assets/base.css';

const app = createApp(App);
const pinia = createPinia();

Object.entries(ElementPlusIconsVue).forEach(([key, component]) => {
  app.component(key, component);
});

app.use(pinia);
app.use(router);
app.use(ElementPlus, {
  locale: zhCn
});

const uiStore = useUiStore(pinia);
uiStore.applyThemeClass();

app.mount('#app');
