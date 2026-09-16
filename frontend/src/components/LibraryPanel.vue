<template>
  <div class="space-y-6 animate-slide-up">
    <!-- Section Heading -->
    <div class="flex flex-wrap items-center justify-between gap-4">
      <div>
        <span class="eyebrow">Thư viện</span>
        <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1 drop-shadow">Thư Viện Module</h2>
        <p class="text-sm text-ink-secondary mt-1">{{ modules.length }} module đã nhập</p>
      </div>
      <button
        @click="fetchModules"
        class="flex items-center gap-2 px-3.5 py-1.5 rounded-pill text-xs font-semibold bg-white/10 border border-glass-borderStrong text-ink-secondary backdrop-blur-md hover:text-ink-primary hover:bg-white/40 hover:scale-[1.02] transition-all duration-300 ease-in-out"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
        </svg>
        Làm mới
      </button>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="card p-16 text-center">
      <svg class="animate-spin-slow w-8 h-8 mx-auto text-pine-400" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
        <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
      </svg>
      <p class="text-sm text-ink-tertiary mt-3">Đang tải danh sách module...</p>
    </div>

    <!-- Empty State -->
    <transition name="fade">
      <div v-if="!loading && modules.length === 0" class="card p-16 text-center">
        <div class="w-16 h-16 mx-auto mb-4 rounded-3xl bg-pine-500/25 flex items-center justify-center">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#8bc7a6" stroke-width="1.3" class="mx-auto">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <p class="text-ink-primary font-medium mb-1">Chưa có bộ đề nào</p>
        <p class="text-sm text-ink-tertiary">Hãy tải lên module PDF đầu tiên từ tab Upload</p>
      </div>
    </transition>

    <!-- Error -->
    <transition name="fade">
      <div v-if="error" class="flex items-center gap-2 text-sm text-semantic-error bg-semantic-error/15 backdrop-blur-md rounded-panel px-4 py-3 border border-semantic-error/30">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        {{ error }}
      </div>
    </transition>

    <!-- Modules Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="m in modules"
        :key="m.id"
        @click="openDetail(m)"
        class="card p-6 space-y-4 group hover:bg-glass-strong hover:scale-[1.02] hover:shadow-glow-wood transition-all duration-300 ease-in-out cursor-pointer"
      >
        <div class="flex items-start justify-between">
          <span class="badge bg-pine-500/15 text-ink-primary ring-1 ring-pine-400/40">Module</span>
          <button
            @click.stop="handleDelete(m)"
            :disabled="deletingId === m.id"
            class="opacity-0 group-hover:opacity-100 transition-all duration-300 text-ink-tertiary hover:text-semantic-error hover:scale-110 p-1.5 -m-1.5 disabled:opacity-40"
            title="Xóa module"
          >
            <svg v-if="deletingId !== m.id" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
            <svg v-else class="animate-spin-slow w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
              <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
            </svg>
          </button>
        </div>

        <div>
          <p class="text-xs font-bold uppercase tracking-wider text-ink-tertiary mb-1">Mã Module</p>
          <h3 class="font-display font-semibold text-ink-primary text-[15px] truncate">Mã Module: {{ m.module_id }}</h3>
        </div>

        <div class="flex items-center gap-2 pt-3 border-t border-glass-border text-xs text-ink-tertiary">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
          </svg>
          <span class="truncate">Ngày tạo: {{ formatDate(m.created_at) }}</span>
        </div>
      </div>
    </div>

    <!-- Module Detail Modal (Phase 18 Req 2) — Teleported to <body> so it escapes
         the app header/panel stacking context (header z-50 bleed fix, Phase 19). -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="detailOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-2 sm:p-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closeDetail"></div>
        <div class="relative glass rounded-panel w-full max-w-[95vw] max-h-[92vh] flex flex-col overflow-hidden">
          <!-- Header -->
          <div class="flex items-center justify-between px-6 py-4 border-b border-glass-border shrink-0">
            <div>
              <p class="font-display font-semibold text-ink-primary">Chi Tiết Module</p>
              <p v-if="detail && !detailLoading" class="text-xs text-ink-tertiary mt-0.5">
                {{ detail.module_id }}<span v-if="detail.created_at" class="ml-2">· tạo {{ formatDate(detail.created_at) }}</span>
              </p>
            </div>
            <button
              @click="closeDetail"
              class="w-9 h-9 rounded-full flex items-center justify-center bg-white/15 text-ink-primary transition-all duration-300 hover:bg-white/25 hover:scale-110"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>
          <!-- Body -->
          <div class="flex-1 min-h-0 overflow-auto p-5 space-y-6">
            <div v-if="detailLoading" class="flex justify-center py-10">
              <svg class="animate-spin-slow w-6 h-6 text-pine-400" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
              </svg>
            </div>
            <p v-if="detailError" class="text-sm text-semantic-error text-center">{{ detailError }}</p>
            <template v-if="detail && !detailLoading">
              <div v-for="group in detailGroups" :key="group.key">
                <p class="text-xs font-bold uppercase tracking-wider text-ink-tertiary mb-2">
                  {{ group.label }} <span class="font-normal normal-case tracking-normal">({{ detail.crops[group.key].length }})</span>
                </p>
                <div v-if="detail.crops[group.key].length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  <div
                    v-for="u in detail.crops[group.key]"
                    :key="u"
                    class="rounded-lg overflow-hidden border border-glass-border bg-black/20 aspect-square cursor-pointer transition-transform duration-200 hover:scale-105 hover:shadow-lg hover:shadow-pine-500/20"
                    @click="openZoom(u)"
                  >
                    <img :src="u" class="w-full h-full object-contain pointer-events-none" loading="lazy" />
                  </div>
                </div>
                <p v-else class="text-xs text-ink-tertiary">Chưa có ảnh cắt cho vùng này</p>
              </div>
              <div>
                <p class="text-xs font-bold uppercase tracking-wider text-ink-tertiary mb-2">
                  Word Assets <span class="font-normal normal-case tracking-normal">({{ detail.word_assets.length }})</span>
                </p>
                <div v-if="detail.word_assets.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                  <div
                    v-for="u in detail.word_assets"
                    :key="u"
                    class="rounded-lg overflow-hidden border border-glass-border bg-black/20 aspect-square cursor-pointer transition-transform duration-200 hover:scale-105 hover:shadow-lg hover:shadow-pine-500/20"
                    @click="openZoom(u)"
                  >
                    <img :src="u" class="w-full h-full object-contain pointer-events-none" loading="lazy" />
                  </div>
                </div>
                <p v-else class="text-xs text-ink-tertiary">Không có word assets</p>
              </div>
            </template>
          </div>
        </div>
      </div>
      </transition>

      <!-- Image Lightbox (Phase 25) — injected after the detail modal, before
           the closing Teleport; Escape + backdrop + failed-load all close. -->
      <transition name="fade">
        <div v-if="zoomedImage" class="fixed inset-0 z-[110] flex items-center justify-center p-2 sm:p-6" @click="closeZoom">
          <div class="absolute inset-0 bg-black/80 backdrop-blur-sm"></div>
          <div class="relative max-w-[95vw] max-h-[92vh] flex flex-col items-center gap-3">
            <img
              :src="zoomedImage"
              @click.stop
              @error="closeZoom"
              class="max-w-full max-h-[92vh] rounded-panel object-contain shadow-2xl shadow-black/60"
              alt="Ảnh phóng to"
            />
          </div>
          <button
            @click.stop="closeZoom"
            class="absolute top-4 right-4 w-10 h-10 rounded-full flex items-center justify-center bg-white/15 text-ink-primary backdrop-blur-md transition-all duration-300 hover:bg-white/25 hover:scale-110"
            title="Đóng (Esc)"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
      </transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useApi } from '../api.js'

const api = useApi()

const modules = ref([])
const loading = ref(false)
const deletingId = ref(null)
const error = ref('')
const detailOpen = ref(false)
const detail = ref(null)
const detailLoading = ref(false)
const detailError = ref('')
const zoomedImage = ref(null)

const detailGroups = computed(() => [
  { key: 'word_preview', label: 'Word Preview' },
  { key: 'excel_preview', label: 'Excel Preview' },
  { key: 'ppt_preview', label: 'PPT Preview' },
  { key: 'word_rubric', label: 'Word Rubric' },
  { key: 'excel_rubric', label: 'Excel Rubric' },
  { key: 'ppt_rubric', label: 'PPT Rubric' },
])

async function openDetail(m) {
  detailError.value = ''
  detail.value = null
  detailOpen.value = true
  detailLoading.value = true
  try {
    detail.value = await api.fetchModuleDetail(m.module_id)
  } catch (e) {
    detailError.value = e.message
  } finally {
    detailLoading.value = false
  }
}

function closeDetail() {
  detailOpen.value = false
  detail.value = null
  detailError.value = ''
}

function openZoom(u) {
  zoomedImage.value = u
}

function closeZoom() {
  zoomedImage.value = null
}

function onKeydown(e) {
  if (e.key === 'Escape') closeZoom()
}

async function fetchModules() {
  loading.value = true
  error.value = ''
  try {
    modules.value = await api.fetchModules()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function handleDelete(m) {
  if (deletingId.value) return
  if (!window.confirm(`Xóa module '${m.module_id}'?\nToàn bộ tệp của module (Word/Excel/PPT) sẽ bị xóa khỏi hệ thống.`)) return
  deletingId.value = m.id
  error.value = ''
  try {
    await api.deleteModule(m.module_id)
    await fetchModules()
  } catch (e) {
    error.value = e.message
  } finally {
    deletingId.value = null
  }
}

function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value.replace(' ', 'T'))
  if (isNaN(d)) return value
  const dd = String(d.getDate()).padStart(2, '0')
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  return `${dd}/${mm}/${d.getFullYear()}`
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
  fetchModules()
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>