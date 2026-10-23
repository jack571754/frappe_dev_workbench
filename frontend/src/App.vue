<template>
  <div class="app-container" id="dev-workbench-root">
    <a class="skip-link" href="#workbench-main">跳到主要内容</a>
    <aside class="workbench-sidebar"><SidebarNav /></aside>
    <div class="workbench-body">
      <HeaderNav @open-navigation="openNavigation" />
      <div class="main-content" id="workbench-main" tabindex="-1"><router-view /></div>
    </div>
    <dialog ref="navigationDialog" class="mobile-navigation" aria-label="导航菜单" @click="closeOnBackdrop"><button class="mobile-nav-close" aria-label="关闭导航" @click="navigationDialog.close()">×</button><SidebarNav @navigate="navigationDialog.close()" /></dialog>
  </div>
</template>

<script setup>
import HeaderNav from '@/components/HeaderNav.vue'
import SidebarNav from '@/components/SidebarNav.vue'
import { ref } from 'vue'
const navigationDialog = ref(null)
function openNavigation() { navigationDialog.value.showModal() }
function closeOnBackdrop(e) { if (e.target === navigationDialog.value) navigationDialog.value.close() }
</script>
