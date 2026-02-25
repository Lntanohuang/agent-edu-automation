import { ref } from 'vue';
import { defineStore } from 'pinia';

export type ThemeMode = 'light' | 'dark';

const THEME_KEY = 'law-assistant.theme';

function getDefaultTheme(): ThemeMode {
  const cachedTheme = localStorage.getItem(THEME_KEY);
  if (cachedTheme === 'light' || cachedTheme === 'dark') {
    return cachedTheme;
  }
  return 'light';
}

export const useUiStore = defineStore('ui', () => {
  const themeMode = ref<ThemeMode>(getDefaultTheme());
  const sidebarCollapsed = ref(false);

  function applyThemeClass() {
    const root = document.documentElement;
    root.classList.toggle('theme-dark', themeMode.value === 'dark');
  }

  function setTheme(mode: ThemeMode) {
    themeMode.value = mode;
    localStorage.setItem(THEME_KEY, mode);
    applyThemeClass();
  }

  function toggleTheme() {
    const next = themeMode.value === 'light' ? 'dark' : 'light';
    setTheme(next);
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }

  return {
    themeMode,
    sidebarCollapsed,
    applyThemeClass,
    setTheme,
    toggleTheme,
    toggleSidebar
  };
});
