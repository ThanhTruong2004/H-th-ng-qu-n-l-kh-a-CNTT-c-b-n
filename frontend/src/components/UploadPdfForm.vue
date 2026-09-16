<template>
  <div class="space-y-6 animate-slide-up">
    <div class="flex items-end justify-between">
      <div>
        <span class="eyebrow">Nhập module</span>
        <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1 drop-shadow">Tải Lên Module PDF</h2>
        <p class="text-sm text-ink-secondary mt-1">Tải lên PDF gốc, sau đó cắt chính xác 6 vùng ảnh (preview & rubric) cho đề thi và đáp án.</p>
      </div>
    </div>

    <form @submit.prevent="handleIngest" class="space-y-8">
      <div class="card p-8 sm:p-10 space-y-8">
        <div>
          <label class="block text-sm font-medium text-ink-primary mb-2">Mã Module <span class="text-semantic-error">*</span></label>
          <input v-model="moduleId" type="text" class="input-field" placeholder="VD: SET_1904C" />
        </div>

        <!-- RAW FILE DROPZONES -->
        <div>
          <label class="block text-sm font-medium text-ink-primary mb-2">File PDF & Tài Nguyên Gốc</label>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div v-for="slot in fileSlots" :key="slot.type">
              <div class="dropzone" :class="{ active: dragOver[slot.type] }"
                   @dragover.prevent="dragOver[slot.type] = true"
                   @dragleave="dragOver[slot.type] = false"
                   @drop.prevent="handleDrop($event, slot.type)"
                   @click="inputEls[slot.type]?.click()">
                <input :ref="(el) => setInputEl(slot.type, el)" type="file" :accept="slot.accept"
                       :multiple="slot.type === 'wordAssets'" class="hidden"
                       @change="onFileChange($event, slot.type)" />
                <template v-if="slot.type === 'wordAssets' ? files.wordAssets.length : files[slot.type]">
                  <div class="flex items-center justify-center gap-3 mb-2">
                    <div class="w-10 h-10 rounded-xl bg-category-word/20 flex items-center justify-center">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#7aa8ff" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
                    </div>
                    <span class="text-sm font-medium text-ink-primary truncate max-w-[200px]">
                      {{ slot.type === 'wordAssets' ? files.wordAssets.length + ' tệp ảnh Word' : (files[slot.type].name) }}
                    </span>
                  </div>
                  <p class="text-xs text-ink-tertiary">{{ slot.type === 'wordAssets' ? '' : formatSize(files[slot.type].size) }}</p>
                  <button type="button" @click.stop="clearSlot(slot.type)" class="mt-2 text-xs font-medium text-semantic-error hover:underline">Loại bỏ</button>
                </template>
                <template v-else>
                  <div class="w-12 h-12 mx-auto mb-3 rounded-2xl bg-white/10 flex items-center justify-center">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#c9d6e3" stroke-width="1.8"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                  </div>
                  <p class="text-sm text-ink-primary font-medium mb-1">{{ slot.title }}</p>
                  <p class="text-xs text-ink-tertiary">{{ slot.hint }}</p>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- CROP SECTION -->
      <div class="card p-8 sm:p-10" v-if="examFile && answerFile">
        <div class="flex items-end justify-between flex-wrap gap-4">
          <div>
            <span class="eyebrow">Bước 03</span>
            <h3 class="font-display text-xl font-bold tracking-tight text-ink-primary mt-1 drop-shadow">Cắt 6 Vùng Ảnh</h3>
            <p class="text-sm text-ink-secondary mt-1">Render các trang PDF thành ảnh rồi kéo khung lấy đúng vùng hình minh họa.</p>
          </div>
          <button v-if="!pagesLoaded" type="button" class="btn-pill flex items-center gap-2"
                  :disabled="renderingPages" @click="loadPages">
            <span v-if="renderingPages">Đang render...</span>
            <span v-else class="flex items-center gap-2">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9" /></svg>
              Render Trang PDF
            </span>
          </button>
        </div>

        <p v-if="pagesError" class="mt-4 text-sm text-semantic-error">{{ pagesError }}</p>

        <template v-if="pagesLoaded">
          <p class="text-sm text-ink-secondary mt-3">Nếu nội dung đáp án kéo dài sang nhiều trang, hãy dùng nút 'Lưu &amp; thêm tiếp' để cắt thành nhiều ảnh cho cùng một phần.</p>
          <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
            <div v-for="slot in cropSlots" :key="slot.key" role="button" tabindex="0"
                 class="text-left p-4 rounded-panel bg-white/5 border border-glass-border hover:bg-white/10 transition-colors duration-300 text-center cursor-pointer"
                 @click="openCropper(slot)"
                 @keydown.space.prevent="openCropper(slot)">
              <div class="flex items-center justify-between mb-1">
                <p class="text-xs font-semibold text-ink-primary">{{ slot.label }}</p>
                <span class="badge" :class="crops[slot.key].length ? 'bg-semantic-success/15 text-ink-primary ring-1 ring-semantic-success/40' : 'bg-white/10 text-ink-tertiary ring-1 ring-glass-border/40'">
                  {{ crops[slot.key].length }}
                </span>
              </div>
              <div v-if="crops[slot.key].length" class="flex flex-wrap gap-1.5 justify-center">
                <div v-for="(c, i) in crops[slot.key]" :key="i" class="group relative">
                  <img :src="c" class="w-14 h-14 object-contain rounded-lg bg-black/20 border border-glass-border" />
                  <button type="button" title="Loại bỏ vùng cắt" @click.stop="removeCrop(slot, i)"
                          class="absolute -top-1.5 -right-1.5 w-5 h-5 rounded-full bg-semantic-error/90 text-white text-[10px] leading-none flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200">&#10005;</button>
                </div>
              </div>
              <div v-else class="h-16 flex flex-col items-center justify-center gap-1 rounded-xl bg-black/20">
                <span class="text-lg text-ink-tertiary">&#10064;</span>
                <span class="text-[11px] text-ink-tertiary">Chưa cắt</span>
              </div>
              <span class="text-[11px] mt-2 inline-flex items-center gap-1"
                    :class="crops[slot.key].length ? 'text-semantic-success' : 'text-ink-tertiary'">
                <span v-if="crops[slot.key].length">{{ crops[slot.key].length }} vùng đã cắt ✓</span>
                <span v-else>Kéo để chọn vùng (nhấp = thêm)</span>
              </span>
            </div>
          </div>
        </template>
      </div>

      <!-- ERROR / SUCCESS -->
      <transition name="fade">
        <div v-if="error" class="flex items-center gap-2 text-sm text-semantic-error bg-semantic-error/15 backdrop-blur-md rounded-panel px-4 py-3 border border-semantic-error/30">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" /></svg>
          {{ error }}
        </div>
      </transition>
      <transition name="fade">
        <div v-if="success" class="flex items-center gap-2 text-sm text-semantic-success bg-semantic-success/15 backdrop-blur-md rounded-panel px-4 py-3 border border-semantic-success/30">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
          {{ success }}
        </div>
      </transition>

      <!-- SUBMIT -->
      <div class="flex justify-end">
        <button type="submit" class="btn-pill flex items-center gap-2"
                :disabled="!canSubmit || generating">
          <span v-if="generating" class="flex items-center gap-2">
            <svg class="animate-spin-slow w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" class="opacity-25" />
              <path d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" class="opacity-75" />
            </svg>
            Đang xử lý...
          </span>
          <span v-else class="flex items-center gap-2">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line x1="12" y1="3" x2="12" y2="15" /></svg>
            Tải Lên Module
          </span>
        </button>
      </div>
    </form>

    <!-- CROPPER MODAL (multi-crop: several crops per section supported) —
         Teleported to <body> so it escapes the panel stacking context and the
         header (z-50) can never bleed through it (Phase 19). -->
    <Teleport to="body">
      <div v-if="showCropper" class="fixed inset-0 z-[100] flex items-center justify-center p-1" @click.self="cancelCrop">
      <div ref="cropperCardRef"
           class="card w-full max-w-[96vw] h-[94vh] p-3 sm:p-4 flex flex-col overflow-hidden"
           :class="fsFallback ? '!w-full !h-[100vh] !max-w-none !rounded-none' : ''">
        <div class="flex items-center justify-between mb-1.5 shrink-0 flex-wrap gap-2">
          <p class="font-display font-bold text-ink-primary">{{ activeSlot.label }}
            <span class="ml-2 badge bg-pine-500/15 text-ink-primary ring-1 ring-pine-400/40">{{ (crops[activeSlot.key] || []).length }} vùng đã cắt</span>
          </p>
          <div class="flex items-center gap-2">
            <button type="button" class="px-3 py-1.5 rounded-pill text-xs font-semibold bg-white/10 border border-glass-borderStrong text-ink-secondary backdrop-blur-md hover:bg-white/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300"
                    @click="changeGroupPage(-1)" :disabled="groupPage <= 0">&#8592; Trang trước</button>
            <span class="text-xs text-ink-tertiary font-semibold">Trang {{ groupPage + 1 }} / {{ groupPages.length }}</span>
            <button type="button" class="px-3 py-1.5 rounded-pill text-xs font-semibold bg-white/10 border border-glass-borderStrong text-ink-secondary backdrop-blur-md hover:bg-white/40 disabled:opacity-40 disabled:cursor-not-allowed transition-all duration-300"
                    @click="changeGroupPage(1)" :disabled="groupPage >= groupPages.length - 1">Trang sau &#8594;</button>
            <button type="button" class="text-ink-tertiary hover:text-ink-primary transition-colors" :title="isFullscreen ? 'Thoát toàn màn hình (Esc)' : 'Toàn màn hình'" @click="toggleFullscreen">
              <svg v-if="!isFullscreen" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
              <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg>
            </button>
            <button type="button" class="text-ink-tertiary hover:text-semantic-error transition-colors" @click="cancelCrop">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
            </button>
          </div>
        </div>
        <div class="rounded-lg overflow-hidden bg-black/30 flex-1 min-h-0 flex items-center justify-center">
          <img ref="cropImgRef" :src="cropSrc" class="h-full w-full object-contain" />
        </div>
        <div class="flex items-center justify-between mt-2 shrink-0 flex-wrap gap-2">
          <button type="button" class="text-xs font-medium text-ink-tertiary hover:text-ink-primary transition-colors" @click="resetCrop">Hoàn tác (reset khung)</button>
          <div class="flex items-center gap-2">
            <button type="button" class="btn-pill-outline" @click="cancelCrop">Huỷ</button>
            <button type="button" class="btn-pill-outline" @click="saveCrop(false)">Lưu &amp; thêm tiếp</button>
            <button type="button" class="btn-pill" @click="saveCrop(true)">Lưu vùng cắt &amp; đóng</button>
          </div>
        </div>
      </div>
    </div>
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
import { reactive, ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import Cropper from 'cropperjs'
import 'cropperjs/dist/cropper.css'
import { useApi } from '../api.js'

const emit = defineEmits(['ingested'])
const api = useApi()

const moduleId = ref('')
const files = reactive({ exam: null, answer: null, wordAssets: [], excel: null, ppt: null })
const dragOver = reactive({ exam: false, answer: false, wordAssets: false, excel: false, ppt: false })
const inputEls = reactive({})

const fileSlots = [
  { type: 'exam', title: 'Đề thi gốc (PDF/Word)', hint: '4 trang, định dạng .pdf/.doc/.docx', accept: '.pdf,.doc,.docx' },
  { type: 'answer', title: 'Đáp án gốc (PDF/Word)', hint: '4 trang, định dạng .pdf/.doc/.docx', accept: '.pdf,.doc,.docx' },
  { type: 'excel', title: 'Excel gốc', hint: 'Định dạng .xlsx', accept: '.xlsx,.xls' },
  { type: 'ppt', title: 'PowerPoint gốc', hint: 'Định dạng .pptx', accept: '.pptx' },
  { type: 'wordAssets', title: 'Ảnh Word Assets', hint: 'Hình ảnh (.png, .jpg, .webp) — tùy chọn, chọn nhiều', accept: 'image/png,image/jpeg,image/webp,image/bmp' },
]

const examFile = computed(() => files.exam)
const answerFile = computed(() => files.answer)

const pagesImages = reactive({ exam: [], answer: [] })
const pagesLoaded = ref(false)
const renderingPages = ref(false)
const pagesError = ref('')
const cropSlots = [
  { key: 'word_preview', label: 'Word Preview', group: 'exam' },
  { key: 'excel_preview', label: 'Excel Preview', group: 'exam' },
  { key: 'ppt_preview', label: 'PPT Preview', group: 'exam' },
  { key: 'word_rubric', label: 'Word Rubric', group: 'answer' },
  { key: 'excel_rubric', label: 'Excel Rubric', group: 'answer' },
  { key: 'ppt_rubric', label: 'PPT Rubric', group: 'answer' },
]

// MULTI-CROP: each section now holds an ARRAY of cropped images (blob object
// URLs — AUDIT-24 ST-5), supporting real-world content that spills across
// multiple pages while keeping JS memory footprint tiny.
const crops = reactive({})
for (const s of cropSlots) crops[s.key] = []

function setInputEl(type, el) {
  if (el) inputEls[type] = el
}

function onFileChange(event, type) {
  const list = Array.from(event.target.files || [])
  assignFiles(list, type)
  error.value = ''
  success.value = ''
}

function handleDrop(event, type) {
  const list = Array.from(event.dataTransfer.files || [])
  assignFiles(list, type)
  dragOver[type] = false
  error.value = ''
  success.value = ''
}

function assignFiles(list, type) {
  if (type === 'wordAssets') {
    files.wordAssets = [...files.wordAssets, ...list]
  } else if (list.length) {
    files[type] = list[0]
    resetCrops()
  }
}

function clearSlot(type) {
  if (type === 'wordAssets') files.wordAssets = []
  else { files[type] = null; resetCrops() }
}

function resetCrops() {
  // AUDIT-24 ST-5: revoke every stored blob object URL before clearing.
  for (const s of cropSlots) {
    for (const u of crops[s.key] || []) {
      if (u && u.startsWith('blob:')) URL.revokeObjectURL(u)
    }
  }
  pagesLoaded.value = false
  pagesImages.exam = []
  pagesImages.answer = []
  for (const s of cropSlots) crops[s.key] = []
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

async function loadPages() {
  if (renderingPages.value) return
  error.value = ''
  pagesError.value = ''
  renderingPages.value = true
  isProcessing.value = true
  processingMessage.value = 'Đang render trang PDF...'
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 50))
  try {
    const res = await api.fetchModulePages(files.exam, files.answer)
    pagesImages.exam = res.exam || []
    pagesImages.answer = res.answer || []
    pagesLoaded.value = true
  } catch (e) {
    pagesError.value = e.message
  } finally {
    renderingPages.value = false
    isProcessing.value = false
  }
}

const showCropper = ref(false)
const activeSlot = ref(null)
const groupPage = ref(0)
const cropSrc = ref('')
const cropImgRef = ref(null)
const cropperCardRef = ref(null)
const isFullscreen = ref(false)
const fsFallback = ref(false)
let cropper = null

// Near-fullscreen cropper (Phase 18 Req 1): explicit fullscreen toggle via the
// Fullscreen API, falling back to CSS classes if the API is unavailable.
function toggleFullscreen() {
  const el = cropperCardRef.value
  if (!el) return
  if (document.fullscreenElement === el) {
    document.exitFullscreen().catch(() => {})
    return
  }
  const req = el.requestFullscreen || el.webkitRequestFullscreen
  if (typeof req === 'function') {
    try {
      req.call(el)
      return
    } catch { /* fall through to CSS fallback */ }
  }
  fsFallback.value = !fsFallback.value
}

function onFsChange() {
  isFullscreen.value = !!document.fullscreenElement
}

onMounted(() => document.addEventListener('fullscreenchange', onFsChange))
onUnmounted(() => document.removeEventListener('fullscreenchange', onFsChange))

const groupPages = computed(() => {
  const slot = activeSlot.value
  return slot ? (pagesImages[slot.group] || []) : []
})

function openCropper(slot) {
  activeSlot.value = slot
  groupPage.value = 0
  cropSrc.value = (pagesImages[slot.group] || [])[0] || ''
  showCropper.value = true
  nextTick(mountCropper)
}

function mountCropper() {
  destroyCropper()
  const img = cropImgRef.value
  if (!img) return
  Promise.resolve(typeof img.decode === 'function' ? img.decode() : null)
    .catch(() => { /* ignore decode failures */ })
    .finally(() => {
      if (!cropImgRef.value) return
      cropper = new Cropper(cropImgRef.value, {
        viewMode: 1,
        dragMode: 'crop',
        autoCropArea: 0.85,
        background: false,
        responsive: true,
        toggleDragModeOnDblclick: false,
      })
    })
}

function changeGroupPage(delta) {
  const pages = groupPages.value
  if (!pages.length) return
  const next = Math.max(0, Math.min(groupPage.value + delta, pages.length - 1))
  if (next === groupPage.value) return
  groupPage.value = next
  cropSrc.value = pages[next]
  nextTick(mountCropper)
}

function destroyCropper() {
  if (cropper) { cropper.destroy(); cropper = null }
}

function resetCrop() {
  if (cropper) cropper.reset()
}

function saveCrop(close = true) {
  if (!cropper) return
  const base = cropper.getCroppedCanvas({
    imageSmoothingEnabled: true,
    imageSmoothingQuality: 'high',
  })
  if (!base) return
  // AUDIT-24 ST-1/ST-5: 2x upscale (was 4x) keeps slow laptops' main thread
  // responsive during encode; thumbnails/PDF overlay don't need 4x detail.
  const scale = 2
  const canvas = document.createElement('canvas')
  canvas.width = base.width * scale
  canvas.height = base.height * scale
  const ctx = canvas.getContext('2d')
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'
  ctx.drawImage(base, 0, 0, canvas.width, canvas.height)
  canvas.toBlob((blob) => {
    if (!blob) return
    // AUDIT-24 ST-5: store an OBJECT URL instead of a Base64 string — the
    // browser keeps the decoded pixels on disk/GPU, not duplicated as a ~33%
    // larger ASCII string in JS memory. Cuts crop memory by ~10x.
    const objectUrl = URL.createObjectURL(blob)
    // MULTI-CROP: push into the ARRAY (several crops per section allowed).
    const key = activeSlot.value.key
    const list = crops[key] || []
    list.push(objectUrl)
    crops[key] = list
    if (close) {
      closeCropper()
    } else {
      // Keep the modal open so the user can crop the next spill-over
      // region on the same (or a neighbouring) page.
      nextTick(mountCropper)
    }
  }, 'image/jpeg', 0.9)
}

function cancelCrop() { closeCropper() }

function closeCropper() {
  destroyCropper()
  showCropper.value = false
  activeSlot.value = null
  groupPage.value = 0
  cropSrc.value = ''
}

function removeCrop(slot, index) {
  if (!Array.isArray(crops[slot.key])) return
  const removed = crops[slot.key].splice(index, 1)
  // AUDIT-24 ST-5: release the object URL we no longer render.
  for (const u of removed) {
    if (u && u.startsWith('blob:')) URL.revokeObjectURL(u)
  }
}

// AUDIT-24 LE-1: a real non-empty file with a valid extension is required —
// guards against 0-byte or mis-typed uploads silently passing the submit.
function isValidRawFile(f) {
  if (!f || typeof f.size !== 'number' || !(f.size > 0)) return false
  const name = (f.name || '').toLowerCase()
  return /\.(pdf|doc|docx)$/.test(name)
}

const canSubmit = computed(() =>
  moduleId.value &&
  isValidRawFile(files.exam) && isValidRawFile(files.answer) &&
  files.excel && files.excel.size > 0 &&
  files.ppt && files.ppt.size > 0 &&
  pagesLoaded.value &&
  cropSlots.every((s) => crops[s.key] && crops[s.key].length > 0)
)

const generating = ref(false)
const isProcessing = ref(false)
const processingMessage = ref('')
const error = ref('')
const success = ref('')

async function dataURLToFile(dataURL, name) {
  const res = await fetch(dataURL)
  const blob = await res.blob()
  return new File([blob], name, { type: blob.type })
}

async function handleIngest() {
  if (!canSubmit.value || generating.value) return
  error.value = ''
  success.value = ''
  generating.value = true
  isProcessing.value = true
  processingMessage.value = 'Đang tải lên module...'
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 50))
  try {
    const cropFiles = {}
    let totalCrops = 0
    for (const slot of cropSlots) {
      const dataURLs = crops[slot.key] || []
      // MULTI-CROP: multiple PNG files per field -> backend stacks them.
      // Use Promise.all to await async dataURLToFile conversions without
      // blocking the UI (AUDIT-23 Fix 1).
      cropFiles[slot.key] = await Promise.all(
        dataURLs.map((dataURL, i) =>
          dataURLToFile(dataURL, `${slot.key}_${i}.png`)))
      totalCrops += dataURLs.length
    }
    await api.ingestModule(
      moduleId.value,
      files.exam,
      files.answer,
      files.wordAssets,
      files.excel,
      files.ppt,
      cropFiles,
    )
    success.value = `Đã tải lên module '${moduleId.value}' với ${totalCrops} vùng ảnh đã cắt.`
    moduleId.value = ''
    for (const k of Object.keys(files)) files[k] = k === 'wordAssets' ? [] : null
    resetCrops()
    emit('ingested')
    setTimeout(() => (success.value = ''), 4000)
  } catch (e) {
    error.value = e.message
  } finally {
    generating.value = false
    isProcessing.value = false
  }
}
</script>