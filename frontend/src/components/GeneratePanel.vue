<template>
  <div class="space-y-6 animate-slide-up">
    <!-- Section Heading -->
    <div>
      <span class="eyebrow">Sinh đề</span>
      <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1 drop-shadow">Tạo Bộ Đề & Xem Trước</h2>
      <p class="text-sm text-ink-secondary mt-1">Ghép các module đã nhập (Word, Excel, PowerPoint) thành bộ đề thi PDF chuẩn quy cách, xem trước hoặc tải về dưới dạng ZIP.</p>
    </div>

    <!-- Module Availability -->
    <div class="card p-8">
      <div class="flex items-center justify-between mb-4">
        <h3 class="font-display font-semibold text-ink-primary">Module Có Sẵn</h3>
        <span class="text-xs text-ink-tertiary">Đã nhập {{ modules.length }} module</span>
      </div>
      <div class="flex flex-wrap gap-2">
        <span
          v-for="m in modules"
          :key="m.id"
          class="badge bg-pine-500/15 text-ink-primary ring-1 ring-pine-400/40"
        >{{ m.module_id }}</span>
        <span v-if="modules.length === 0" class="text-sm text-ink-tertiary">
          Chưa có module nào. Hãy tải lên module PDF ở tab Upload trước.
        </span>
      </div>
    </div>

    <!-- Generator Form -->
    <div class="card p-8 sm:p-10">
      <form @submit.prevent="handleGenerate" class="space-y-8">
        <!-- Exam Info -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label class="block text-sm font-medium text-ink-primary mb-2">Ngày Thi <span class="text-semantic-error">*</span></label>
            <input
              v-model="ngayThi"
              type="date"
              class="input-field [color-scheme:dark]"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-ink-primary mb-2">Mã Đề <span class="text-semantic-error">*</span></label>
            <input
              v-model="maDe"
              type="text"
              class="input-field"
              placeholder="VD: 1904C"
            />
          </div>
          <div>
            <label class="block text-sm font-medium text-ink-primary mb-2">Cán Bộ Ra Đáp Án</label>
            <input
              v-model="canBoRaDe"
              type="text"
              class="input-field"
              placeholder="Trương Việt Hoa"
            />
          </div>
        </div>

        <!-- Module Selection -->
        <div>
          <div class="flex items-center justify-between mb-3">
            <label class="block text-sm font-medium text-ink-primary">Chọn Module</label>
            <div class="flex items-center gap-3">
            <span class="text-sm font-medium text-ink-primary">Chế độ:</span>
            <button
              type="button"
              @click="setRandomMode(true)"
              :class="randomToggle ? 'bg-pine-500 text-white' : 'bg-white/10 text-white/50'"
              class="px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all duration-300 ease-in-out hover:bg-pine-400/80"
            >
              Ngẫu nhiên
            </button>
            <button
              type="button"
              @click="setRandomMode(false)"
              :class="!randomToggle ? 'bg-amber-600 text-white' : 'bg-white/10 text-white/50'"
              class="px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-all duration-300 ease-in-out hover:bg-amber-500/80"
            >
              Thủ công
            </button>
          </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div v-for="field in moduleFields" :key="field.key">
              <label class="block text-sm font-medium text-ink-primary mb-2">{{ field.label }}</label>
              <select
                v-model="field.value"
                :disabled="randomToggle"
                class="w-full px-4 py-3 rounded-pill border border-glass-borderStrong bg-glass-light text-ink-primary text-sm backdrop-blur-md transition-all duration-300 ease-in-out [color-scheme:dark] focus:outline-none focus:ring-2 focus:ring-pine-400/60 focus:border-pine-300 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                <option v-for="m in modules" :key="m.id" :value="m.id">{{ m.module_id }}</option>
              </select>
            </div>
          </div>
        </div>

        <!-- Error -->
        <transition name="fade">
          <div v-if="error" class="flex items-center gap-2 text-sm text-semantic-error bg-semantic-error/15 backdrop-blur-md rounded-panel px-4 py-3 border border-semantic-error/30">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            {{ error }}
          </div>
        </transition>

        <!-- Success -->
        <transition name="fade">
          <div v-if="success" class="flex items-center gap-2 text-sm text-semantic-success bg-semantic-success/15 backdrop-blur-md rounded-panel px-4 py-3 border border-semantic-success/30">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            {{ success }}
          </div>
        </transition>

        <!-- Actions -->
        <div class="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-3">
          <button
            type="button"
            class="btn-secondary"
            :disabled="!canGenerate || previewing || generating"
            @click="handlePreview"
          >
            <span v-if="previewing" class="flex items-center gap-2 justify-center">
              <svg class="animate-spin-slow w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
              </svg>
              Đang tạo bản xem trước...
            </span>
            <span v-else class="flex items-center gap-2 justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
              Xem Trước (Preview)
            </span>
          </button>

          <button
            type="submit"
            class="btn-pill"
            :disabled="!canGenerate || previewing || generating"
          >
            <span v-if="generating" class="flex items-center gap-2 justify-center">
              <svg class="animate-spin-slow w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
              </svg>
              Đang đóng gói ZIP...
            </span>
            <span v-else class="flex items-center gap-2 justify-center">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Tạo Đề & Tải ZIP
            </span>
          </button>
        </div>
      </form>
    </div>

    <!-- Preview Modal — Teleported to <body> to escape the panel stacking
         context (header z-50 bleed fix, Phase 19). -->
    <Teleport to="body">
      <transition name="fade">
        <div v-if="previewOpen" class="fixed inset-0 z-[100] flex items-center justify-center p-2 sm:p-4">
        <div class="absolute inset-0 bg-black/70 backdrop-blur-sm" @click="closePreview"></div>
        <div class="relative glass rounded-panel w-full max-w-[95vw] h-[90vh] flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-6 py-4 border-b border-glass-border">
            <div>
              <p class="font-display font-semibold text-ink-primary">Xem Trước Bộ Đề — Mã đề {{ maDe || '—' }}</p>
              <p class="text-xs text-ink-tertiary mt-0.5">Đề thi 4 trang & Đáp án 4 trang</p>
            </div>
            <button
              @click="closePreview"
              class="w-9 h-9 rounded-full flex items-center justify-center bg-white/15 text-ink-primary transition-all duration-300 hover:bg-white/25 hover:scale-110"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
          </div>

          <div class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 overflow-auto">
            <div class="flex flex-col min-h-0">
              <p class="text-xs font-bold uppercase tracking-wider text-ink-tertiary mb-2">Đề Thi</p>
              <div class="flex-1 min-h-0 rounded-panel overflow-hidden bg-white/10 border border-glass-border">
                <iframe v-if="examPreviewUrl" :src="examPreviewUrl" class="w-full h-full"></iframe>
              </div>
            </div>
            <div class="flex flex-col min-h-0">
              <p class="text-xs font-bold uppercase tracking-wider text-ink-tertiary mb-2">Đáp Án</p>
              <div class="flex-1 min-h-0 rounded-panel overflow-hidden bg-white/10 border border-glass-border">
                <iframe v-if="answerPreviewUrl" :src="answerPreviewUrl" class="w-full h-full"></iframe>
              </div>
            </div>
          </div>

          <div class="px-6 py-4 border-t border-glass-border flex justify-end">
            <button class="btn-pill" @click="closePreview">Đóng</button>
          </div>
        </div>
      </div>
      </transition>
    </Teleport>
  </div>
  <!-- Blocking loader — Teleported to <body>, z-200 blocks absolutely
       everything (header, modals, etc.). -->
  <Teleport to="body">
    <div v-if="isProcessing" class="fixed inset-0 z-[200] flex flex-col items-center justify-center bg-black/40 backdrop-blur-sm">
      <div class="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-emerald-500 mb-4"></div>
      <p class="text-white text-lg font-medium shadow-sm">{{ processingMessage }}</p>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useApi } from '../api.js'

const api = useApi()

const ngayThi = ref('')
const maDe = ref('')
const canBoRaDe = ref('Trương Việt Hoa')
const modules = ref([])
const randomToggle = ref(true)
const wordModuleId = ref(null)
const excelModuleId = ref(null)
const pptModuleId = ref(null)

const previewOpen = ref(false)
const examPreviewUrl = ref('')
const answerPreviewUrl = ref('')
const generationId = ref('')
const previewing = ref(false)
const generating = ref(false)
const isProcessing = ref(false)
const processingMessage = ref('')
const error = ref('')
const success = ref('')

const moduleFields = computed(() => [
  { key: 'word', label: 'Module Word', value: wordModuleId },
  { key: 'excel', label: 'Module Excel', value: excelModuleId },
  { key: 'ppt', label: 'Module PowerPoint', value: pptModuleId },
])

const canGenerate = computed(() => {
  return (
    modules.value.length > 0 &&
    !!maDe.value.trim() &&
    !!ngayThi.value &&
    (randomToggle.value || (wordModuleId.value && excelModuleId.value && pptModuleId.value))
  )
})

function setRandomMode(isRandom) {
  randomToggle.value = isRandom
  if (isRandom) {
    // Random mode: explicitly clear any default IDs so they never leak into
    // the payload — the backend picks an independent module per category.
    wordModuleId.value = null
    excelModuleId.value = null
    pptModuleId.value = null
  } else if (modules.value.length > 0) {
    // Manual mode: fall back to the newest uploaded module by default.
    wordModuleId.value = modules.value[0].id
    excelModuleId.value = modules.value[0].id
    pptModuleId.value = modules.value[0].id
  }
}

async function fetchModules() {
  modules.value = await api.fetchModules()
  setRandomMode(randomToggle.value)
}

function buildPayload() {
  return {
    ngay_thi: ngayThi.value,
    ma_de: maDe.value.trim(),
    can_bo_ra_de: canBoRaDe.value.trim() || 'Trương Việt Hoa',
    random: randomToggle.value,
    word_module_id: randomToggle.value ? null : Number(wordModuleId.value),
    excel_module_id: randomToggle.value ? null : Number(excelModuleId.value),
    ppt_module_id: randomToggle.value ? null : Number(pptModuleId.value),
  }
}

async function handlePreview() {
  if (!canGenerate.value || previewing.value) return
  error.value = ''
  previewing.value = true
  isProcessing.value = true
  processingMessage.value = 'Đang sinh đề thi...'
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 50))
  try {
    const res = await api.generatePreview(buildPayload())
    generationId.value = res.generation_id || ''
    // Preview the SAME artifact that will be downloaded (no double generation).
    examPreviewUrl.value = res.exam_url || ''
    answerPreviewUrl.value = res.answer_url || ''
    previewOpen.value = true
  } catch (e) {
    error.value = e.message
  } finally {
    previewing.value = false
    isProcessing.value = false
  }
}

function closePreview() {
  examPreviewUrl.value = ''
  answerPreviewUrl.value = ''
  previewOpen.value = false
}

// Any change to the request inputs invalidates the stored artifact — the user
// must Preview again before Download so ZIP is always built from fresh PDFs.
watch(
  [ngayThi, maDe, canBoRaDe, randomToggle, wordModuleId, excelModuleId, pptModuleId],
  () => {
    generationId.value = ''
    if (previewOpen.value) closePreview()
  }
)

async function handleGenerate() {
  if (!canGenerate.value || generating.value) return
  error.value = ''
  success.value = ''
  if (!generationId.value) {
    error.value = 'Vui lòng bấm Xem Trước trước để tạo bộ đề, sau đó mới tải ZIP.'
    return
  }
  generating.value = true
  isProcessing.value = true
  processingMessage.value = 'Đang đóng gói ZIP...'
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 50))
  try {
    await api.generateDownload({
      generation_id: generationId.value,
      ma_de: maDe.value.trim(),
    })
    success.value = `Đã tạo và tải xuống bộ đề mã ${maDe.value.trim()} thành công!`
    setTimeout(() => success.value = '', 3000)
  } catch (e) {
    error.value = e.message
  } finally {
    generating.value = false
    isProcessing.value = false
  }
}

onMounted(fetchModules)
</script>