<template>
  <div class="space-y-6 animate-slide-up">
    <!-- Section Heading -->
    <div>
      <span class="eyebrow">Sinh đề</span>
      <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1">Tạo Bộ Đề Ngẫu Nhiên</h2>
      <p class="text-sm text-ink-secondary mt-1">Chọn ngẫu nhiên đề thi và tổng hợp tiêu chí chấm điểm thành một gói tải xuống duy nhất.</p>
    </div>

    <!-- Requirements Check -->
    <div class="card p-8">
      <div class="flex items-center justify-between mb-5">
        <h3 class="font-display font-semibold text-ink-primary">Điều Kiện Cần Thiết</h3>
        <span class="text-xs text-ink-tertiary">Cần đủ 3 nhóm</span>
      </div>
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div class="flex items-center gap-3 p-4 rounded-panel" :class="props.stats.word_count > 0 ? 'bg-semantic-success/5 border border-semantic-success/20' : 'bg-semantic-error/5 border border-semantic-error/20'">
          <div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0" :class="props.stats.word_count > 0 ? 'bg-semantic-success/20' : 'bg-semantic-error/20'">
            <svg v-if="props.stats.word_count > 0" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2FA06A" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#C4453B" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-semibold" :class="props.stats.word_count > 0 ? 'text-semantic-success' : 'text-semantic-error'">{{ props.stats.word_count }} Word</p>
            <p class="text-[11px] text-ink-tertiary truncate">Cần tệp .docx</p>
          </div>
        </div>
        <div class="flex items-center gap-3 p-4 rounded-panel" :class="props.stats.excel_count > 0 ? 'bg-semantic-success/5 border border-semantic-success/20' : 'bg-semantic-error/5 border border-semantic-error/20'">
          <div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0" :class="props.stats.excel_count > 0 ? 'bg-semantic-success/20' : 'bg-semantic-error/20'">
            <svg v-if="props.stats.excel_count > 0" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2FA06A" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#C4453B" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-semibold" :class="props.stats.excel_count > 0 ? 'text-semantic-success' : 'text-semantic-error'">{{ props.stats.excel_count }} Excel</p>
            <p class="text-[11px] text-ink-tertiary truncate">Cần tệp .xlsx</p>
          </div>
        </div>
        <div class="flex items-center gap-3 p-4 rounded-panel" :class="props.stats.powerpoint_count > 0 ? 'bg-semantic-success/5 border border-semantic-success/20' : 'bg-semantic-error/5 border border-semantic-error/20'">
          <div class="w-9 h-9 rounded-full flex items-center justify-center shrink-0" :class="props.stats.powerpoint_count > 0 ? 'bg-semantic-success/20' : 'bg-semantic-error/20'">
            <svg v-if="props.stats.powerpoint_count > 0" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#2FA06A" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
            <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#C4453B" stroke-width="3"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </div>
          <div class="min-w-0">
            <p class="text-sm font-semibold" :class="props.stats.powerpoint_count > 0 ? 'text-semantic-success' : 'text-semantic-error'">{{ props.stats.powerpoint_count }} Slides</p>
            <p class="text-[11px] text-ink-tertiary truncate">Cần tệp .pptx</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Generator Controls -->
    <div class="card p-8 sm:p-10">
      <div class="flex flex-col sm:flex-row items-stretch sm:items-center gap-6">
        <div class="flex-1">
          <label class="block text-sm font-medium text-ink-primary mb-3">Số Lượng Bộ Đề Cần Tạo</label>
          <div class="flex items-center gap-3">
            <button
              @click="count = Math.max(1, count - 1)"
              class="w-11 h-11 rounded-2xl border border-brand-900/15 flex items-center justify-center text-brand-700 hover:bg-brand-50 transition-default"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <input
              v-model.number="count"
              type="number"
              min="1"
              max="50"
              class="w-20 text-center input-field font-display text-xl font-bold text-brand-700"
            />
            <button
              @click="count = Math.min(50, count + 1)"
              class="w-11 h-11 rounded-2xl border border-brand-900/15 flex items-center justify-center text-brand-700 hover:bg-brand-50 transition-default"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
          </div>
          <p class="text-xs text-ink-tertiary mt-3">Mỗi bộ: 1 Word + 1 Excel + 1 Slides + bảng tiêu chí ghép</p>
        </div>

        <div class="sm:self-center">
          <button
            @click="handleGenerate"
            :disabled="!canGenerate || api.loading.value"
            class="btn-pill text-[15px] w-full sm:w-auto justify-center"
          >
            <span v-if="api.loading.value" class="flex items-center gap-2 justify-center">
              <svg class="animate-spin w-5 h-5" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
              </svg>
              Đang tạo...
            </span>
            <span v-else class="flex items-center gap-2">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                <polygon points="2 7 12 12 22 7"/>
                <line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
              </svg>
              Tạo {{ count }} Bộ Đề
            </span>
          </button>
        </div>
      </div>

      <!-- Error -->
      <div v-if="error" class="mt-5 flex items-center gap-2 text-sm text-semantic-error bg-semantic-error/5 rounded-panel px-4 py-3">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
        {{ error }}
      </div>
    </div>

    <!-- Generated Results -->
    <div v-if="results.length > 0" class="card p-8">
      <div class="flex items-center justify-between mb-5">
        <h3 class="font-display font-semibold text-ink-primary">Kết Quả Đã Tạo ({{ results.length }})</h3>
        <button @click="downloadAll" class="text-sm font-semibold text-brand-700 hover:text-brand-800 transition-default">Tải tất cả</button>
      </div>
      <div class="space-y-2.5">
        <div
          v-for="(result, idx) in results"
          :key="result.id"
          class="flex items-center justify-between gap-3 p-4 rounded-panel bg-canvas-100/70 border border-brand-900/[0.06] hover:border-brand-600/20 transition-default group"
        >
          <div class="flex items-center gap-3 min-w-0">
            <span class="font-display text-sm font-bold text-ink-tertiary w-6 shrink-0">{{ String(idx + 1).padStart(2, '0') }}</span>
            <div class="flex items-center gap-2 flex-wrap min-w-0">
              <span class="badge-word !text-[10px] py-0.5 truncate max-w-[140px]">{{ result.word_exam }}</span>
              <span class="text-ink-tertiary text-[10px] shrink-0">+</span>
              <span class="badge-excel !text-[10px] py-0.5 truncate max-w-[140px]">{{ result.excel_exam }}</span>
              <span class="text-ink-tertiary text-[10px] shrink-0">+</span>
              <span class="badge-powerpoint !text-[10px] py-0.5 truncate max-w-[140px]">{{ result.ppt_exam }}</span>
            </div>
          </div>
          <button
            @click="api.downloadFile(result.filename)"
            class="flex items-center gap-1.5 text-sm font-semibold text-brand-700 hover:text-brand-800 shrink-0 opacity-60 hover:opacity-100 transition-all"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Tải
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useApi } from '../api.js'

const props = defineProps({
  stats: { type: Object, default: () => ({ word_count: 0, excel_count: 0, powerpoint_count: 0 }) }
})

const emit = defineEmits(['generated'])
const api = useApi()

const count = ref(1)
const results = ref([])
const error = ref('')

const canGenerate = computed(() => {
  return props.stats.word_count > 0 && props.stats.excel_count > 0 && props.stats.powerpoint_count > 0
})

async function handleGenerate() {
  error.value = ''
  try {
    const res = await api.generateExams(count.value)
    results.value = [...res.sets, ...results.value]
    emit('generated')
  } catch (e) {
    error.value = e.message
  }
}

async function downloadAll() {
  for (const r of results.value) {
    await api.downloadFile(r.filename)
    await new Promise(resolve => setTimeout(resolve, 500))
  }
}
</script>
