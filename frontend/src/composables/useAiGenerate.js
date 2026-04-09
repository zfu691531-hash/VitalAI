import { ref } from 'vue'

export function useAiGenerate(requester, options = {}) {
  const loading = ref(false)
  const error = ref('')
  const result = ref(options.initialResult ?? null)
  const lastParams = ref(null)

  async function generate(params) {
    loading.value = true
    error.value = ''
    lastParams.value = params

    try {
      const response = await requester(params)
      result.value = response
      return response
    } catch (err) {
      error.value = err.message || '生成失败，请稍后重试'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function retry() {
    if (!lastParams.value) {
      return null
    }
    return generate(lastParams.value)
  }

  function reset(nextValue = null) {
    result.value = nextValue
    error.value = ''
    loading.value = false
  }

  return {
    loading,
    error,
    result,
    lastParams,
    generate,
    retry,
    reset
  }
}
