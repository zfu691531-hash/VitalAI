<template>
  <div class="page-container">
    <AiChatPanel
      title="校规问答机器人"
      subtitle="支持连续追问，适合学生、家长和老师快速核对校规。"
      :messages="messages"
      :loading="loading"
      placeholder="例如：手机被收走后多久可以领取？"
      assistant-label="校规助手"
      show-download
      @send="handleSend"
      @clear="handleClear"
      @download="handleDownload"
    />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'
import { askRule } from '@/api/aiTools'
import { getAiHistoryDetail } from '@/api/aiHistory'
import { downloadWordDocument, formatChatTranscript } from '@/utils/export'

const route = useRoute()

const messages = ref([])
const loading = ref(false)

onMounted(async () => {
  await loadHistory(route.query.historyId)
})

watch(
  () => route.query.historyId,
  async (historyId, prevId) => {
    if (historyId && historyId !== prevId) {
      await loadHistory(historyId)
    }
  }
)

async function handleSend(question) {
  loading.value = true
  messages.value.push({ role: 'user', content: question })

  try {
    const res = await askRule({
      question,
      chat_history: buildHistory()
    })
    messages.value.push({ role: 'assistant', content: res.answer })
  } catch (error) {
    ElMessage.error(error.message || '问答失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

function buildHistory() {
  const pairs = []
  let currentQuestion = ''

  messages.value.forEach((item) => {
    if (item.role === 'user') {
      currentQuestion = item.content
    } else if (item.role === 'assistant' && currentQuestion) {
      pairs.push({
        question: currentQuestion,
        answer: item.content
      })
    }
  })

  return pairs.slice(-5)
}

function handleClear() {
  messages.value = []
}

async function loadHistory(historyId) {
  if (!historyId) {
    return
  }

  const detail = await getAiHistoryDetail(Number(historyId))
  const question = detail.input_params?.question
  messages.value = []

  if (question) {
    messages.value.push({ role: 'user', content: question })
  }

  messages.value.push({ role: 'assistant', content: detail.content })
}

function handleDownload() {
  const transcript = formatChatTranscript(messages.value, {
    user: '提问',
    assistant: '校规助手'
  })
  downloadWordDocument('校规问答记录', transcript, '校规问答记录.doc')
}
</script>
