<template>
  <div class="page-container ai-page">
    <div class="ai-layout">
      <el-card shadow="never">
        <template #header>
          <div>
            <div class="card-title">违纪处理话术</div>
            <div class="card-desc">输入事件场景后，AI 会生成适合学生或家长沟通的完整表达。</div>
          </div>
        </template>

        <el-form :model="form" label-width="90px">
          <el-form-item label="学生姓名">
            <el-input v-model="form.student_name" placeholder="请输入学生姓名" />
          </el-form-item>
          <el-form-item label="事件描述">
            <el-input v-model="form.incident" type="textarea" :rows="5" placeholder="例如：课间与同学争执并推搡" />
          </el-form-item>
          <el-form-item label="沟通语气">
            <el-select v-model="form.mode" class="full-width">
              <el-option label="温和" value="温和" />
              <el-option label="严肃" value="严肃" />
            </el-select>
          </el-form-item>
          <el-form-item label="沟通对象">
            <el-select v-model="form.target" class="full-width">
              <el-option label="学生" value="学生" />
              <el-option label="家长" value="家长" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleGenerate">生成话术</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <AiOutputPanel
        title="沟通话术"
        subtitle="适合班主任快速整理家校沟通文本。"
        :content="result?.script || ''"
        :loading="loading"
        :error="error"
        show-download
        @retry="handleGenerate"
        @download="handleDownload"
      />
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiOutputPanel from '@/components/ai/AiOutputPanel.vue'
import { useAiGenerate } from '@/composables/useAiGenerate'
import { generateDiscipline } from '@/api/aiTools'
import { getAiHistoryDetail } from '@/api/aiHistory'
import { downloadWordDocument } from '@/utils/export'

const route = useRoute()

const form = reactive({
  incident: '',
  student_name: '',
  mode: '温和',
  target: '学生'
})

const { loading, error, result, generate } = useAiGenerate(generateDiscipline)

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

async function handleGenerate() {
  if (!form.student_name || !form.incident) {
    ElMessage.warning('请先补全学生姓名和事件描述')
    return
  }

  await generate({ ...form })
}

async function loadHistory(historyId) {
  if (!historyId) {
    return
  }

  const detail = await getAiHistoryDetail(Number(historyId))
  Object.assign(form, detail.input_params || {})
  result.value = { script: detail.content }
}

function handleDownload() {
  downloadWordDocument('违纪处理话术', result.value?.script || '', '违纪处理话术.doc')
}
</script>

<style scoped lang="scss">
.ai-layout {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
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

.full-width {
  width: 100%;
}

@media (max-width: 960px) {
  .ai-layout {
    grid-template-columns: 1fr;
  }
}
</style>
