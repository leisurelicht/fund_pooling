<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppSidebar from '@/components/app/AppSidebar.vue'
import { logout } from '@/auth/session'

const route = useRoute()
const router = useRouter()
const showChrome = computed(() => !route.meta.public)
const loggingOut = ref(false)

const COLLAPSE_KEY = 'sidebar-collapsed'
const collapsed = ref(localStorage.getItem(COLLAPSE_KEY) === '1')

function toggleSidebar() {
  collapsed.value = !collapsed.value
  localStorage.setItem(COLLAPSE_KEY, collapsed.value ? '1' : '0')
}

async function handleLogout() {
  if (loggingOut.value) return
  loggingOut.value = true
  try {
    await logout()
    await router.push({ name: 'login' })
  } finally {
    loggingOut.value = false
  }
}
</script>

<template>
  <div
    v-if="showChrome"
    class="app-layout"
    :class="{ 'app-layout--collapsed': collapsed }"
  >
    <AppSidebar
      :logging-out="loggingOut"
      :collapsed="collapsed"
      @logout="handleLogout"
      @toggle="toggleSidebar"
    />
    <main class="app-main">
      <router-view />
    </main>
  </div>
  <div v-else class="app--plain">
    <router-view />
  </div>
</template>