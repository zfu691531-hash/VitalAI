<template>
  <div class="page-container interview-page">
    <el-card shadow="never" class="interview-config">
      <template #header>
        <div>
          <div class="card-title">模拟面试官</div>
          <div class="card-desc">先选择面试场景，AI 会逐轮追问并在结束时给出总结反馈。</div>
        </div>
      </template>

      <el-form :model="form" inline>
        <el-form-item label="面试类型">
          <el-select v-model="form.interview_type" class="wide-select">
            <el-option label="自主招生" value="自主招生" />
            <el-option label="社团招新" value="社团招新" />
            <el-option label="班干部竞选" value="班干部竞选" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生">
          <el-select v-model="form.student_id" clearable filterable class="wide-select" placeholder="可选">
            <el-option v-for="item in studentOptions" :key="item.id" :label="item.name" :value="item.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="startInterview">开始面试</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <AiChatPanel
      title="模拟面试对话"
      subtitle="AI 会结合你的上一轮回答继续追问，直到给出总结评价。"
      :messages="messages"
      :loading="loading"
      placeholder="输入你的回答"
      assistant-label="面试官"
      show-download
      @send="handleAnswer"
      @clear="clearConversation"
      @download="handleDownload"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'
import { mockInterview } from '@/api/aiTools'
import { getStudentList } from '@/api/student'
import { getAiHistoryDetail } from '@/api/aiHistory'
import { downloadWordDocument, formatChatTranscript } from '@/utils/export'

const route = useRoute()
const studentOptions = ref([])
const loading = ref(false)
const messages = ref([])
const historyPairs = ref([])
const currentQuestion = ref('')
const finished = ref(false)

const form = reactive({
  interview_type: '自主招生',
  student_id: ''
})

onMounted(async () => {
  await fetchStudents()
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

async function fetchStudents() {
  const res = await getStudentList({ page: 1, page_size: 100 })
  studentOptions.value = res.list
}

async function startInterview() {
  loading.value = true
  clearConversation()

  try {
    const res = await mockInterview({
      interview_type: form.interview_type,
      student_id: form.student_id || undefined
    })
    currentQuestion.value = res.content
    messages.value.push({ role: 'assistant', content: res.content })
  } catch (error) {
    ElMessage.error(error.message || '启动模拟面试失败')
  } finally {
    loading.value = false
  }
}

async function handleAnswer(answer) {
  if (!currentQuestion.value && !messages.value.length) {
    ElMessage.warning('请先点击“开始面试”')
    return
  }

  if (finished.value) {
    ElMessage.warning('本轮面试已结束，请重新开始')
    return
  }

  loading.value = true
  messages.value.push({ role: 'user', content: answer })

  try {
    const res = await mockInterview({
      interview_type: form.interview_type,
      student_id: form.student_id || undefined,
      answer,
      chat_history: historyPairs.value
    })
    historyPairs.value.push({
      question: currentQuestion.value,
      answer
    })
    currentQuestion.value = res.is_finished ? '' : res.content
    finished.value = res.is_finished
    messages.value.push({ role: 'assistant', content: res.content })
  } catch (error) {
    ElMessage.error(error.message || '提交回答失败')
  } finally {
    loading.value = false
  }
}

function clearConversation() {
  messages.value = []
  historyPairs.value = []
  currentQuestion.value = ''
  finished.value = false
}

async function loadHistory(historyId) {
  if (!historyId) {
    return
  }

  const detail = await getAiHistoryDetail(Number(historyId))
  Object.assign(form, detail.input_params || {})
  clearConversation()
  messages.value.push({ role: 'assistant', content: detail.content })
  finished.value = true
}

function handleDownload() {
  const transcript = formatChatTranscript(messages.value, {
    user: '学生',
    assistant: '面试官'
  })
  downloadWordDocument('模拟面试记录', transcript, '模拟面试记录.doc')
}
</script>

<style scoped lang="scss">
.interview-page {
  display: grid;
  gap: 16px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
}

.card-desc {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.wide-select {
  width: 220px;
}
</style>
