<template>
  <div class="page-container rag-page">
    <el-alert
      title="新版校规问答已进入试运行，支持回答反馈和管理员持续优化。旧版校规问答仍可继续使用。"
      type="info"
      :closable="false"
      show-icon
      class="page-alert"
    />

    <div class="rag-layout">
      <AiChatPanel
        title="新版校规问答"
        subtitle="支持混合检索、命中来源展示和回答反馈。"
        :messages="messages"
        :loading="loading"
        placeholder="例如：手机被收走后多久可以拿回来？"
        assistant-label="校规助手"
        show-download
        @send="handleSend"
        @clear="handleClear"
        @download="handleDownload"
      />

      <el-card shadow="never" class="side-card">
        <template #header>
          <div>
            <div class="card-title">回答反馈</div>
            <div class="card-desc">对最新一次回答进行评价，管理员会在反馈中心处理并优化知识库。</div>
          </div>
        </template>

        <el-form :model="feedbackForm" label-width="84px">
          <el-form-item label="满意度">
            <el-radio-group v-model="feedbackForm.rating">
              <el-radio label="up">满意</el-radio>
              <el-radio label="down">不满意</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="改进理由">
            <el-input
              v-model="feedbackForm.improvement_reason"
              type="textarea"
              :rows="4"
              placeholder="可以描述哪里不准确、哪里还不够清楚。"
            />
          </el-form-item>
          <el-form-item label="建议答案">
            <el-input
              v-model="feedbackForm.suggested_answer"
              type="textarea"
              :rows="4"
              placeholder="如果你有更好的答案，也可以补充给管理员参考。"
            />
          </el-form-item>
          <el-button
            type="primary"
            :disabled="!latestQaRecordId"
            :loading="feedbackLoading"
            @click="handleSubmitFeedback"
          >
            提交反馈
          </el-button>
        </el-form>

        <el-divider />

        <div class="card-title">命中来源</div>
        <el-empty v-if="!latestSources.length" description="提问后这里会展示命中的校规片段。" />
        <div v-else class="sources-list">
          <el-card v-for="item in latestSources" :key="item.chunk_id" shadow="never" class="source-item">
            <div class="source-head">
              <span>校规 #{{ item.rule_id }}</span>
              <span>融合分：{{ item.scores?.fused }}</span>
            </div>
            <div class="source-text">{{ item.chunk_text }}</div>
          </el-card>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import AiChatPanel from '@/components/ai/AiChatPanel.vue'
import { askRuleRag, submitRuleRagFeedback } from '@/api/ruleRag'
import { downloadWordDocument, formatChatTranscript } from '@/utils/export'

const messages = ref([])
const loading = ref(false)
const feedbackLoading = ref(false)
const latestQaRecordId = ref(null)
const latestSources = ref([])

const feedbackForm = ref({
  rating: 'up',
  improvement_reason: '',
  suggested_answer: ''
})

async function handleSend(question) {
  loading.value = true
  messages.value.push({ role: 'user', content: question })

  try {
    const res = await askRuleRag({
      question,
      chat_history: buildHistory()
    })
    latestQaRecordId.value = res.qa_record_id
    latestSources.value = res.sources || []
    messages.value.push({ role: 'assistant', content: res.answer })
  } catch (error) {
    ElMessage.error(error.message || '新版校规问答暂时不可用')
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
      pairs.push({ question: currentQuestion, answer: item.content })
    }
  })
  return pairs.slice(-5)
}

async function handleSubmitFeedback() {
  if (!latestQaRecordId.value) {
    ElMessage.warning('请先完成一次问答')
    return
  }

  feedbackLoading.value = true
  try {
    await submitRuleRagFeedback({
      qa_record_id: latestQaRecordId.value,
      rating: feedbackForm.value.rating,
      improvement_reason: feedbackForm.value.improvement_reason,
      suggested_answer: feedbackForm.value.suggested_answer
    })
    ElMessage.success('反馈已提交')
    feedbackForm.value.improvement_reason = ''
    feedbackForm.value.suggested_answer = ''
  } finally {
    feedbackLoading.value = false
  }
}

function handleClear() {
  messages.value = []
  latestQaRecordId.value = null
  latestSources.value = []
}

function handleDownload() {
  const transcript = formatChatTranscript(messages.value, {
    user: '提问',
    assistant: '新版校规助手'
  })
  downloadWordDocument('新版校规问答记录', transcript, '新版校规问答记录.doc')
}
</script>

<style scoped lang="scss">
.page-alert {
  margin-bottom: 16px;
}

.rag-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 16px;
}

.side-card {
  align-self: start;
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

.sources-list {
  display: grid;
  gap: 12px;
}

.source-item {
  border: 1px solid #e5e7eb;
}

.source-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 12px;
  color: #64748b;
}

.source-text {
  font-size: 13px;
  line-height: 1.7;
  color: #334155;
  white-space: pre-wrap;
}

@media (max-width: 1100px) {
  .rag-layout {
    grid-template-columns: 1fr;
  }
}
</style>
