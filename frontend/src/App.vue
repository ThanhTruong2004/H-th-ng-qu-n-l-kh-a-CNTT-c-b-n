<template>
  <div class="relative min-h-screen overflow-x-hidden">
    <!-- Fixed Full-Screen Background (switches per tab) -->
    <div class="dlu-bg" :style="{ backgroundImage: `url(${currentBg})` }"></div>
    <!-- Dark overlay for readability -->
    <div class="dlu-overlay"></div>

    <!-- Background credits / label -->
    <p class="content-layer fixed bottom-2 right-3 z-30 text-[10px] text-white/40 tracking-wide select-none">
      Đại học Đà Lạt
    </p>

    <!-- Sticky Glass Header -->
    <header class="header-layer sticky top-0 px-4 sm:px-6 pt-4">
      <div class="glass max-w-6xl mx-auto rounded-full flex items-center justify-between px-5 py-2.5 transition-all duration-300 ease-in-out hover:bg-glass-dark">
        <!-- Brand -->
        <div class="flex items-center gap-3">
          <img
            src="/colorful-itc-logo.png"
            alt="ICT DLU Logo"
            class="h-12 w-auto object-contain"
          />
        </div>

        <!-- Desktop Nav -->
        <nav class="hidden sm:flex items-center gap-1">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-4 py-1.5 rounded-full text-[13px] font-medium transition-all duration-300 ease-in-out',
              activeTab === tab.id
                ? 'bg-green-600 text-white font-semibold rounded-full shadow-[0_0_15px_rgba(22,163,74,0.4)] transition-all duration-300 hover:bg-green-500 hover:scale-105 hover:shadow-[0_0_20px_rgba(22,163,74,0.6)]'
                : 'text-ink-secondary hover:text-ink-primary hover:bg-white/40 hover:scale-[1.02]'
            ]"
          >
            {{ tab.label }}
          </button>
        </nav>

        <!-- Mobile menu button -->
        <button
          class="sm:hidden w-9 h-9 rounded-full flex items-center justify-center bg-white/15 text-ink-primary transition-all duration-300 hover:bg-white/25 hover:scale-105"
          @click="mobileOpen = !mobileOpen"
        >
          <svg v-if="!mobileOpen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
          <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Mobile nav -->
      <div v-if="mobileOpen" class="sm:hidden max-w-6xl mx-auto mt-2 glass rounded-3xl p-2 animate-fade-in">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          @click="activeTab = tab.id; mobileOpen = false"
          :class="[
            'block w-full text-left px-4 py-2.5 rounded-full text-sm font-medium transition-all duration-300',
            activeTab === tab.id ? 'bg-green-600 text-white font-semibold rounded-full shadow-[0_0_15px_rgba(22,163,74,0.4)]' : 'text-ink-secondary hover:bg-white/40 hover:text-ink-primary'
          ]"
        >
          {{ tab.label }}
        </button>
      </div>
    </header>

    <!-- Hero / Brand Banner -->
    <section class="content-layer relative max-w-6xl mx-auto px-6 pt-12 pb-8 text-center">
      <div class="inline-flex items-center gap-2 mb-6 animate-fade-in">
        <span class="h-px w-8 bg-wood-300/60"></span>
        <span class="eyebrow">Đại học Đà Lạt</span>
        <span class="h-px w-8 bg-wood-300/60"></span>
      </div>

      <h1 class="font-display text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-white text-balance animate-slide-up drop-shadow-lg" style="text-shadow: 0 4px 6px rgba(0,0,0,0.5);">
        Quản lý<br class="sm:hidden" /> <span class="text-pine-300">khóa CNTT cơ bản</span>
      </h1>

      <p class="mt-4 max-w-xl mx-auto text-white text-sm sm:text-base leading-relaxed animate-slide-up-slow drop-shadow" style="text-shadow: 0 2px 4px rgba(0,0,0,0.6);">
        Hệ thống tự động chọn bộ đề ngẫu nhiên và bảng tiêu chí chấm điểm tương ứng thành một bộ đề duy nhất.
      </p>
    </section>

    <!-- Main Content -->
    <main class="content-layer max-w-6xl mx-auto px-6 pb-16">
      <UploadPdfForm v-if="activeTab === 'upload'" />
      <LibraryPanel v-else-if="activeTab === 'library'" />
      <GeneratePanel v-else-if="activeTab === 'generate'" />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import UploadPdfForm from './components/UploadPdfForm.vue'
import LibraryPanel from './components/LibraryPanel.vue'
import GeneratePanel from './components/GeneratePanel.vue'

const activeTab = ref('generate')
const mobileOpen = ref(false)

const tabs = [
  { id: 'upload', label: 'Upload', bg: '/bg-dlu-flycam.jpg' },
  { id: 'library', label: 'Library', bg: '/bg-vnur.jpg' },
  { id: 'generate', label: 'Generate', bg: '/bg-dlu-flycam.jpg' },
]

const currentBg = computed(() => {
  const tab = tabs.find(t => t.id === activeTab.value)
  return tab ? tab.bg : '/bg-dlu-flycam.jpg'
})
</script>
