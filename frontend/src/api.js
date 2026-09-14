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

  async function ingestModule(moduleId, examPdf, answerKeyPdf, wordAssets, excelFile, pptFile, crops = {}) {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('module_id', moduleId)
      formData.append('exam_raw_pdf', examPdf)
      formData.append('answer_key_raw_pdf', answerKeyPdf)
      for (const f of wordAssets) {
        formData.append('word_assets', f)
      }
      formData.append('excel_raw_file', excelFile)
      formData.append('ppt_raw_file', pptFile)
      for (const [key, list] of Object.entries(crops)) {
        const files = Array.isArray(list) ? list : (list ? [list] : [])
        for (const file of files) {
          if (file) formData.append(key, file)
        }
      }
      return await request('/modules/ingest', { method: 'POST', body: formData })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchModulePages(examPdf, answerKeyPdf) {
    loading.value = true
    error.value = null
    try {
      const formData = new FormData()
      if (examPdf) formData.append('exam_raw_pdf', examPdf)
      if (answerKeyPdf) formData.append('answer_key_raw_pdf', answerKeyPdf)
      return await request('/modules/pages', { method: 'POST', body: formData })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchModules() {
    return request('/modules')
  }

  async function deleteModule(moduleId) {
    loading.value = true
    error.value = null
    try {
      return await request(`/modules/${encodeURIComponent(moduleId)}`, { method: 'DELETE' })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function generatePreview(payload) {
    loading.value = true
    error.value = null
    try {
      return await request('/generate/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchBlob(url) {
    const res = await fetch(url)
    if (!res.ok) throw new Error('Failed to load preview')
    return res.blob()
  }

  async function generateDownload(payload) {
    loading.value = true
    error.value = null
    try {
      const res = await fetch(`${API_BASE}/generate/download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }))
        throw new Error(err.detail || 'Request failed')
      }
      const blob = await res.blob()
      const disposition = res.headers.get('Content-Disposition') || ''
      const match = disposition.match(/filename="?([^";]+)"?/i)
      const filename = match ? match[1] : 'DLU_Exam.zip'
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      return { filename }
    } catch (e) {
      error.value = e.message
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    loading,
    error,
    ingestModule,
    fetchModulePages,
    fetchModules,
    deleteModule,
    generatePreview,
    generateDownload,
    fetchBlob,
  }
}