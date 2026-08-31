<template>
  <div class="space-y-6 animate-slide-up">
    <!-- Section Heading -->
    <div class="flex items-end justify-between">
      <div>
        <span class="eyebrow">Step 01</span>
        <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1">Upload Bộ Đề Thi</h2>
      </div>
      <div v-if="selectedCategory" class="hidden sm:block">
        <span :class="categoryBadgeClass">{{ selectedCategory }}</span>
      </div>
    </div>

    <!-- Upload Form -->
    <div class="card p-8 sm:p-10">
      <form @submit.prevent="handleUpload" class="space-y-8">
        <!-- Name Input -->
        <div>
          <label class="block text-sm font-medium text-ink-primary mb-2">Tên Bộ Đề <span class="text-ink-tertiary font-normal">(Tùy chọn)</span></label>
          <input
            v-model="setName"
            type="text"
            class="input-field"
            placeholder="VD: Đề CK CNTT - 2024"
          />
        </div>

        <!-- File Upload Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <!-- Exam File -->
          <div>
            <label class="block text-sm font-medium text-ink-primary mb-2">Tệp Đề Thi</label>
            <div
              class="dropzone"
              :class="{ active: examDragOver }"
              @dragover.prevent="examDragOver = true"
              @dragleave="examDragOver = false"
              @drop.prevent="handleDrop($event, 'exam')"
              @click="examInput?.click()"
            >
              <input
                ref="examInput"
                type="file"
                accept=".docx,.xlsx,.xls,.pptx"
                class="hidden"
                @change="handleFileSelect($event, 'exam')"
              />
              <template v-if="examFile">
                <div class="flex items-center justify-center gap-3 mb-2">
                  <div class="w-10 h-10 rounded-xl flex items-center justify-center" :class="categoryIconBg">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" :stroke="categoryColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-ink-primary truncate max-w-[220px]">{{ examFile.name }}</span>
                </div>
                <p class="text-xs text-ink-tertiary">{{ formatSize(examFile.size) }}</p>
                <button
                  type="button"
                  @click.stop="examFile = null"
                  class="mt-2 text-xs font-medium text-semantic-error hover:underline"
                >Loại bỏ</button>
              </template>
              <template v-else>
                <div class="w-12 h-12 mx-auto mb-3 rounded-2xl bg-brand-50 flex items-center justify-center">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0F766E" stroke-width="1.8" class="mx-auto">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="17 8 12 3 7 8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                </div>
                <p class="text-sm text-ink-primary font-medium mb-1">Kéo thả đề thi vào đây hoặc nhấn chọn</p>
                <p class="text-xs text-ink-tertiary">Hỗ trợ .docx, .xlsx, .pptx</p>
              </template>
            </div>
          </div>

          <!-- Criteria File -->
          <div>
            <label class="block text-sm font-medium text-ink-primary mb-2">Tiêu Chí Chấm Điểm</label>
            <div
              class="dropzone"
              :class="{ active: criteriaDragOver }"
              @dragover.prevent="criteriaDragOver = true"
              @dragleave="criteriaDragOver = false"
              @drop.prevent="handleDrop($event, 'criteria')"
              @click="criteriaInput?.click()"
            >
              <input
                ref="criteriaInput"
                type="file"
                accept=".xlsx"
                class="hidden"
                @change="handleFileSelect($event, 'criteria')"
              />
              <template v-if="criteriaFile">
                <div class="flex items-center justify-center gap-3 mb-2">
                  <div class="w-10 h-10 rounded-xl bg-category-excel/10 flex items-center justify-center">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="2">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-ink-primary truncate max-w-[220px]">{{ criteriaFile.name }}</span>
                </div>
                <p class="text-xs text-ink-tertiary">{{ formatSize(criteriaFile.size) }}</p>
                <button
                  type="button"
                  @click.stop="criteriaFile = null"
                  class="mt-2 text-xs font-medium text-semantic-error hover:underline"
                >Loại bỏ</button>
              </template>
              <template v-else>
                <div class="w-12 h-12 mx-auto mb-3 rounded-2xl bg-category-excel/10 flex items-center justify-center">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#16a34a" stroke-width="1.8">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  </svg>
                </div>
                <p class="text-sm text-ink-primary font-medium mb-1">Kéo thả tiêu chí chấm điểm</p>
                <p class="text-xs text-ink-tertiary">Chỉ chấp nhận định dạng .xlsx</p>
              </template>
            </div>
          </div>
        </div>

        <!-- Error -->
        <div v-if="error" class="flex items-center gap-2 text-sm text-semantic-error bg-semantic-error/5 rounded-panel px-4 py-3">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          {{ error }}
        </div>

        <!-- Success -->
        <div v-if="success" class="flex items-center gap-2 text-sm text-semantic-success bg-semantic-success/5 rounded-panel px-4 py-3">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
          {{ success }}
        </div>

        <!-- Submit -->
        <div class="flex justify-end">
          <button
            type="submit"
            class="btn-pill"
            :disabled="!examFile || !criteriaFile || api.loading.value"
          >
            <span v-if="api.loading.value" class="flex items-center gap-2">
              <svg class="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25"/>
                <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75"/>
              </svg>
              Đang tải...
            </span>
            <span v-else class="flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              Tải Lên Bộ Đề
            </span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useApi } from '../api.js'

const emit = defineEmits(['uploaded'])
const api = useApi()

const examFile = ref(null)
const criteriaFile = ref(null)
const setName = ref('')
const examDragOver = ref(false)
const criteriaDragOver = ref(false)
const error = ref('')
const success = ref('')
const examInput = ref(null)
const criteriaInput = ref(null)

const selectedCategory = computed(() => {
  if (!examFile.value) return null
  const ext = examFile.value.name.split('.').pop().toLowerCase()
  if (ext === 'docx') return 'Word'
  if (ext === 'xlsx' || ext === 'xls') return 'Excel'
  if (ext === 'pptx') return 'PowerPoint'
  return null
})

const categoryBadgeClass = computed(() => {
  const cat = selectedCategory.value?.toLowerCase()
  if (cat === 'word') return 'badge-word'
  if (cat === 'excel') return 'badge-excel'
  if (cat === 'powerpoint') return 'badge-powerpoint'
  return 'badge'
})

const categoryColor = computed(() => {
  const cat = selectedCategory.value?.toLowerCase()
  if (cat === 'word') return '#2563eb'
  if (cat === 'excel') return '#16a34a'
  if (cat === 'powerpoint') return '#dc2626'
  return '#0F766E'
})

const categoryIconBg = computed(() => {
  const cat = selectedCategory.value?.toLowerCase()
  if (cat === 'word') return 'bg-category-word/10'
  if (cat === 'excel') return 'bg-category-excel/10'
  if (cat === 'powerpoint') return 'bg-category-powerpoint/10'
  return 'bg-brand-50'
})

function handleFileSelect(event, type) {
  const file = event.target.files[0]
  if (type === 'exam') {
    examFile.value = file
  } else {
    criteriaFile.value = file
  }
  error.value = ''
  success.value = ''
}

function handleDrop(event, type) {
  const file = event.dataTransfer.files[0]
  if (type === 'exam') {
    examFile.value = file
    examDragOver.value = false
  } else {
    criteriaFile.value = file
    criteriaDragOver.value = false
  }
  error.value = ''
  success.value = ''
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function handleUpload() {
  if (!examFile.value || !criteriaFile.value) return
  error.value = ''
  success.value = ''
  try {
    await api.uploadSet(examFile.value, criteriaFile.value, setName.value)
    success.value = 'Đã tải lên thành công! Bộ đề đã có trong thư viện.'
    examFile.value = null
    criteriaFile.value = null
    setName.value = ''
    emit('uploaded')
    setTimeout(() => success.value = '', 3000)
  } catch (e) {
    error.value = e.message
  }
}
</script>
