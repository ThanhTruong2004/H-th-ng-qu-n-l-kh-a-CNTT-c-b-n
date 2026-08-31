import { ref } from 'vue'

const API_BASE = '/api'

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, {
    headers: { ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export function useApi() {
  const loading = ref(false)
  const error = ref(null)

  async function fetchStats() {
    return request('/stats')
  }

  async function fetchSets(category = null) {
    const params = category ? `?category=${category}` : ''
    return request(`/sets${params}`)
  }

  async function uploadSet(examFile, criteriaFile, name = '') {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('exam', examFile)
      formData.append('criteria', criteriaFile)
      formData.append('name', name)
      return await request('/sets/upload', { method: 'POST', body: formData })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteSet(id) {
    loading.value = true
    error.value = null
    try {
      return await request(`/sets/${id}`, { method: 'DELETE' })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function generateExams(count = 1) {
    loading.value = true
    error.value = null
    try {
      return await request('/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ count }),
      })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function downloadFile(filename) {
    const res = await fetch(`${API_BASE}/download/${filename}`)
    if (!res.ok) throw new Error('Download failed')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  async function fetchGenerated() {
    return request('/generated')
  }

  async function deleteGenerated(id) {
    return request(`/generated/${id}`, { method: 'DELETE' })
  }

  return {
    loading,
    error,
    fetchStats,
    fetchSets,
    uploadSet,
    deleteSet,
    generateExams,
    downloadFile,
    fetchGenerated,
    deleteGenerated,
  }
}
