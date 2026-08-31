<template>
  <div class="space-y-6 animate-slide-up">
    <!-- Section Heading -->
    <div class="flex items-center justify-between gap-4">
      <div>
        <span class="eyebrow">Thư viện</span>
        <h2 class="font-display text-2xl font-bold tracking-tight text-ink-primary mt-1">Kho Đề Thi</h2>
        <p class="text-sm text-ink-secondary mt-1">{{ filteredSets.length }} bộ đề trong bộ sưu tập</p>
      </div>
      <div class="flex gap-2">
        <button
          v-for="cat in categories"
          :key="cat.id"
          @click="activeFilter = cat.id"
          :class="[
            'px-3.5 py-1.5 rounded-pill text-xs font-semibold transition-default',
            activeFilter === cat.id
              ? 'bg-brand-800 text-white shadow-soft'
              : 'bg-white/80 border border-brand-900/15 text-ink-secondary hover:text-brand-800 hover:border-brand-600/30'
          ]"
        >
          {{ cat.label }}
        </button>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="filteredSets.length === 0" class="card p-16 text-center">
      <div class="w-16 h-16 mx-auto mb-4 rounded-3xl bg-brand-50 flex items-center justify-center">
        <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#0F766E" stroke-width="1.3" class="mx-auto">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        </svg>
      </div>
      <p class="text-ink-primary font-medium mb-1">Chưa có bộ đề nào</p>
      <p class="text-sm text-ink-tertiary">Hãy tải lên bộ đề đầu tiên để bắt đầu</p>
    </div>

    <!-- Sets Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div
        v-for="set in filteredSets"
        :key="set.id"
        class="card p-6 space-y-4 group hover:-translate-y-1 hover:shadow-hover transition-all duration-300"
      >
        <div class="flex items-start justify-between">
          <span :class="getBadgeClass(set.category)">{{ set.category }}</span>
          <button
            @click="$emit('delete', set.id)"
            class="opacity-0 group-hover:opacity-100 transition-all text-ink-tertiary hover:text-semantic-error p-1.5 -m-1.5"
            title="Xóa"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>

        <div>
          <h3 class="font-display font-semibold text-ink-primary text-[15px] mb-1 truncate">{{ set.name }}</h3>
          <p class="text-xs text-ink-tertiary truncate">{{ set.exam_filename }}</p>
        </div>

        <div class="flex items-center gap-2 pt-3 border-t border-brand-900/[0.06] text-xs text-ink-tertiary">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="3" x2="9" y2="21"/>
          </svg>
          <span class="truncate">Tiêu chí: {{ set.criteria_filename }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  sets: { type: Array, default: () => [] }
})

defineEmits(['delete', 'refresh'])

const activeFilter = ref('all')

const categories = [
  { id: 'all', label: 'Tất cả' },
  { id: 'word', label: 'Word' },
  { id: 'excel', label: 'Excel' },
  { id: 'powerpoint', label: 'Slides' },
]

const filteredSets = computed(() => {
  if (activeFilter.value === 'all') return props.sets
  return props.sets.filter(s => s.category === activeFilter.value)
})

function getBadgeClass(category) {
  if (category === 'word') return 'badge-word'
  if (category === 'excel') return 'badge-excel'
  if (category === 'powerpoint') return 'badge-powerpoint'
  return 'badge'
}
</script>
