import { computed, ref } from 'vue';
import { defineStore } from 'pinia';
import type { UserProfile, UserRole } from '@/types';

const TOKEN_KEY = 'law-assistant.token';
const PROFILE_KEY = 'law-assistant.profile';

const roleLabelMap: Record<UserRole, string> = {
  partner: '合伙人',
  lawyer: '律师',
  intern: '实习生'
};

const roleNameMap: Record<UserRole, string> = {
  partner: '陈合伙人',
  lawyer: '李律师',
  intern: '王实习生'
};

function readProfileFromStorage() {
  const raw = localStorage.getItem(PROFILE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as UserProfile;
  } catch {
    return null;
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY));
  const profile = ref<UserProfile | null>(readProfileFromStorage());

  const isAuthenticated = computed(() => Boolean(token.value));
  const roleLabel = computed(() => {
    if (!profile.value) {
      return '';
    }
    return roleLabelMap[profile.value.role];
  });

  function loginWithRole(role: UserRole) {
    token.value = `mock-token-${Date.now()}`;
    profile.value = {
      id: `u-${role}`,
      role,
      tenantName: '星海律师事务所',
      name: roleNameMap[role]
    };
    localStorage.setItem(TOKEN_KEY, token.value);
    localStorage.setItem(PROFILE_KEY, JSON.stringify(profile.value));
  }

  function logout() {
    token.value = null;
    profile.value = null;
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PROFILE_KEY);
  }

  function hasRole(roles?: UserRole[]) {
    if (!roles || roles.length === 0) {
      return true;
    }
    if (!profile.value) {
      return false;
    }
    return roles.includes(profile.value.role);
  }

  return {
    token,
    profile,
    isAuthenticated,
    roleLabel,
    loginWithRole,
    logout,
    hasRole
  };
});
