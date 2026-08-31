<template>
  <div class="relative min-h-screen bg-canvas-50 overflow-x-hidden">
    <!-- Ambient background glow -->
    <div class="pointer-events-none fixed inset-0 bg-grain" aria-hidden="true"></div>

    <!-- Sticky Glass Header -->
    <header class="sticky top-0 z-50 mt-4 px-4">
      <div class="glass-pill max-w-6xl mx-auto flex items-center justify-between px-5 py-2.5">
        <!-- Brand -->
        <div class="flex items-center gap-3">
          <img
            src="/logo-full.png"
            alt="ICT DLU"
            class="w-9 h-9 rounded-[10px] object-contain ring-1 ring-brand-900/10 shadow-soft"
          />
          <div class="leading-none">
            <p class="font-display text-[15px] font-bold tracking-tight text-ink-primary">ICT DLU</p>
            <p class="text-[9px] font-semibold uppercase tracking-widest-2 text-brand-700 mt-0.5">Exam Manager</p>
          </div>
        </div>

        <!-- Nav -->
        <nav class="hidden sm:flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-4 py-1.5 rounded-pill text-[13px] font-medium transition-default',
              activeTab === tab.id
                ? 'bg-brand-800 text-white shadow-soft'
                : 'text-ink-secondary hover:text-brand-800 hover:bg-brand-50'
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>

        <!-- Mobile menu button -->
        <button
          class="sm:hidden w-9 h-9 rounded-full flex items-center justify-center bg-brand-50 text-brand-800"
          @click="mobileOpen = !mobileOpen"
        >
          <svg v-if="!mobileOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Mobile nav -->
      <div v-if="mobileOpen" class="sm:hidden max-w-6xl mx-auto mt-2 glass-pill p-2 animate-fade-in">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id; mobileOpen = false"
          :class="[
            'block w-full text-left px-4 py-2.5 rounded-pill text-sm font-medium transition-default',
            activeTab === tab.id ? 'bg-brand-800 text-white' : 'text-ink-secondary hover:bg-brand-50'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </header>

    <!-- Hero / Brand Banner -->
    <section class="relative max-w-6xl mx-auto px-6 pt-12 pb-8 text-center">
      <div class="inline-flex items-center gap-2 mb-6 animate-fade-in">
        <span class="h-px w-8 bg-brand-600/40"></span>
        <span class="eyebrow">Đại học Đà Lạt</span>
        <span class="h-px w-8 bg-brand-600/40"></span>
      </div>

      <h1 class="font-display text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-ink-primary text-balance animate-slide-up">
        Quản lý &amp; Sinh<br class="sm:hidden" />
        <span class="text-brand-700">đề thi CNTT</span>
      </h1>

      <p class="mt-4 max-w-xl mx-auto text-ink-secondary text-sm sm:text-base leading-relaxed animate-slide-up-slow">
        Hệ thống lưu trữ đề thi theo tệp, tự động chọn ngẫu nhiên và tổng hợp bảng tiêu chí chấm điểm thành một gói tải xuống duy nhất.
      </p>

      <!-- Quick stats -->
      <div class="mt-8 grid grid-cols-3 max-w-xl mx-auto gap-3 animate-slide-up-slow">
        <div class="glass-pill px-4 py-3">
          <p class="font-display text-2xl font-bold text-brand-700">{{ stats.word_count }}</p>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-secondary">Word</p>
        </div>
        <div class="glass-pill px-4 py-3">
          <p class="font-display text-2xl font-bold text-brand-700">{{ stats.excel_count }}</p>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-secondary">Excel</p>
        </div>
        <div class="glass-pill px-4 py-3">
          <p class="font-display text-2xl font-bold text-brand-700">{{ stats.powerpoint_count }}</p>
          <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-secondary">Slide</p>
        </div>
      </div>
    </section>

    <!-- Main Content -->
    <main class="max-w-6xl mx-auto px-6 pb-16">
      <transition name="fade" mode="out-in">
        <UploadPanel v-if="activeTab === 'upload'" @uploaded="refreshAll" />
        <LibraryPanel v-else-if="activeTab === 'library'" :sets="sets" @delete="handleDelete" @refresh="fetchSets" />
        <GeneratePanel v-else-if="activeTab === 'generate'" :stats="stats" @generated="refreshAll" />
      </transition>
    </main>

    <!-- Footer -->
    <footer class="border-t border-brand-900/10 mt-8">
      <div class="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        <p class="text-xs text-ink-tertiary">ICT DLU &middot; Trường Đại học Đà Lạt</p>
        <p class="text-xs text-ink-tertiary">Generated Exam Management System v1.0</p>
      </div>
    </footer>

    <div class="bg-grain-overlay" aria-hidden="true"></div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useApi } from './api.js'
import UploadPanel from './components/UploadPanel.vue'
import LibraryPanel from './components/LibraryPanel.vue'
import GeneratePanel from './components/GeneratePanel.vue'

const api = useApi()
const activeTab = ref('generate')
const mobileOpen = ref(false)
const stats = ref({ word_count: 0, excel_count: 0, powerpoint_count: 0, total: 0 })
const sets = ref([])

const tabs = [
  { id: 'upload', label: 'Upload' },
  { id: 'library', label: 'Library' },
  { id: 'generate', label: 'Generate' },
]

async function refreshStats() {
  stats.value = await api.fetchStats()
}

async function fetchSets() {
  sets.value = await api.fetchSets()
}

async function refreshAll() {
  await Promise.all([refreshStats(), fetchSets()])
}

async function handleDelete(id) {
  await api.deleteSet(id)
  await refreshAll()
}

onMounted(refreshAll)
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
