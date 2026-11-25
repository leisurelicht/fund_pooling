<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { session } from '@/auth/session'

const props = defineProps<{ loggingOut: boolean; collapsed: boolean }>()
const emit = defineEmits<{ logout: []; toggle: [] }>()

const menuOpen = ref(false)

/** 折叠侧栏时收回用户菜单，否则 72px 宽里文字会被挤成竖排 */
watch(
  () => props.collapsed,
  (collapsed) => {
    if (collapsed) menuOpen.value = false
  },
)

/**
 * 折叠态没有横向空间放下拉菜单，点击头像先展开侧栏再弹菜单。
 * 展开由父组件完成，这里立即把菜单置为打开，避免等一次渲染。
 */
function toggleMenu() {
  if (props.collapsed) {
    emit('toggle')
    menuOpen.value = true
    return
  }
  menuOpen.value = !menuOpen.value
}

const username = computed(() => session.user?.username ?? '')
const avatarLetter = computed(() => username.value.charAt(0).toUpperCase())

/** 单色线性图标：统一 24 视窗、1.75 描边，随文字着色 */
const navItems = [
  {
    to: '/',
    label: '总览',
    icon: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  },
  {
    to: '/transactions',
    label: '交易',
    icon: 'M7 4v16M4 7l3-3 3 3M17 20V4M14 17l3 3 3-3',
  },
  {
    to: '/sips',
    label: '定投',
    icon: 'M5 5h14a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V6a1 1 0 011-1zM4 9h16M8 3v4M16 3v4',
  },
  {
    to: '/analysis',
    label: '分析',
    icon: 'M4 20V4M4 20h16M8 16l4-5 3 2 4-6',
  },
  {
    to: '/settings',
    label: '设置',
    icon: 'M4 8h5M13 8h7M11 6a2 2 0 1 1 0 4a2 2 0 1 1 0-4M4 15h8M16 15h4M14 13a2 2 0 1 1 0 4a2 2 0 1 1 0-4',
  },
]
</script>

<template>
  <aside class="sidebar" :class="{ 'sidebar--collapsed': collapsed }">
    <button
      class="sidebar__toggle"
      type="button"
      :title="collapsed ? '展开侧边栏' : '折叠侧边栏'"
      :aria-label="collapsed ? '展开侧边栏' : '折叠侧边栏'"
      @click="emit('toggle')"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M15 6l-6 6 6 6" />
      </svg>
    </button>

    <div class="sidebar__inner">
      <div class="sidebar__brand">
        <span class="sidebar__logo" aria-hidden="true">账</span>
        <span class="sidebar__title">资产账本</span>
      </div>

      <nav class="sidebar__nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="sidebar__link"
          active-class="sidebar__link--active"
          :title="collapsed ? item.label : undefined"
          :aria-label="item.label"
        >
          <svg
            class="sidebar__icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path :d="item.icon" />
          </svg>
          <span class="sidebar__label">{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__user">
        <button
          class="sidebar__user-btn"
          type="button"
          :title="collapsed ? username : undefined"
          :aria-label="username"
          @click="toggleMenu"
        >
          <span class="sidebar__avatar">{{ avatarLetter }}</span>
          <span class="sidebar__username">{{ username }}</span>
        </button>
        <div v-if="menuOpen" class="sidebar__menu">
          <button
            class="sidebar__menu-item sidebar__menu-item--danger"
            type="button"
            :disabled="loggingOut"
            @click="emit('logout')"
          >
            {{ loggingOut ? '退出中…' : '退出登录' }}
          </button>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: var(--sb-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  /* 本体不裁剪：折叠按钮悬在右边缘外，需要能溢出 */
  overflow: visible;
  z-index: 100;
  transition: width 0.2s ease;
}

/* 滚动容器放在内层，避免把溢出的折叠按钮一起裁掉 */
.sidebar__inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar__toggle {
  position: absolute;
  top: 24px;
  right: -11px;
  z-index: 110;
  width: 22px;
  height: 22px;
  display: grid;
  place-items: center;
  padding: 0;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-muted);
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(16, 20, 28, 0.1);
  transition:
    color 0.15s ease,
    border-color 0.15s ease,
    transform 0.2s ease;
}

.sidebar__toggle svg {
  width: 12px;
  height: 12px;
}

.sidebar--collapsed .sidebar__toggle {
  transform: rotate(180deg);
}

.sidebar__toggle:hover {
  color: var(--accent);
  border-color: var(--accent);
}

.sidebar__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 12px 18px;
  min-width: 0;
}

.sidebar__logo {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 9px;
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 0.03em;
  color: #fff;
  background: var(--accent);
  flex-shrink: 0;
}

.sidebar__title {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -0.01em;
  color: var(--text-strong);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar__nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 4px;
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 8px;
  border-radius: 9px;
  font-size: 16px;
  font-weight: 500;
  color: var(--text);
  text-decoration: none;
  white-space: nowrap;
  transition:
    background 0.15s ease,
    color 0.15s ease;
}

.sidebar__link:hover {
  background: var(--surface-muted);
  color: var(--text-strong);
}

.sidebar__link:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.sidebar__link--active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}

.sidebar__icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.sidebar__user {
  position: relative;
  padding: 12px 4px 16px;
  border-top: 1px solid var(--border);
  margin-top: auto;
}

.sidebar__user-btn {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 10px;
  width: 100%;
  padding: 6px 8px;
  border: none;
  border-radius: 8px;
  background: transparent;
  cursor: pointer;
  transition: background 0.15s ease;
}

.sidebar__user-btn:hover {
  background: var(--surface-muted);
}

.sidebar__avatar {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 700;
  color: var(--accent);
  background: var(--accent-soft);
  flex-shrink: 0;
}

.sidebar__username {
  font-size: 15px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar__menu {
  position: absolute;
  bottom: 100%;
  left: 10px;
  right: 10px;
  margin-bottom: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 4px;
  box-shadow: var(--shadow);
  z-index: 200;
}

.sidebar__menu-item {
  display: block;
  width: 100%;
  white-space: nowrap;
  padding: 8px 10px;
  border: none;
  border-radius: 6px;
  background: transparent;
  font-size: 13.5px;
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: background 0.15s ease;
}

.sidebar__menu-item:hover {
  background: var(--surface-muted);
}

.sidebar__menu-item--danger {
  color: var(--error);
}

.sidebar__menu-item--danger:hover {
  background: var(--error-soft);
}

/* ---------- 折叠态 ---------- */

.sidebar--collapsed .sidebar__brand {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.sidebar--collapsed .sidebar__nav {
  padding: 0 10px;
}

/* 折叠态：图标放大并严格居中，行做成等高方块 */
.sidebar--collapsed .sidebar__link {
  justify-content: center;
  align-items: center;
  gap: 0;
  width: 100%;
  height: 44px;
  padding: 0;
}

.sidebar--collapsed .sidebar__label,
.sidebar--collapsed .sidebar__title,
.sidebar--collapsed .sidebar__username {
  display: none;
}

.sidebar--collapsed .sidebar__user-btn {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

.sidebar--collapsed .sidebar__icon {
  width: 22px;
  height: 22px;
}
</style>