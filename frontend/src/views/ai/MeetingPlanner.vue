<template>
  <div class="page-container ai-page">
    <div class="ai-layout">
      <el-card shadow="never">
        <template #header>
          <div>
            <div class="card-title">班会活动策划</div>
            <div class="card-desc">输入主题和年级，快速拿到可执行的完整班会方案。</div>
          </div>
        </template>

        <el-form :model="form" label-width="90px">
          <el-form-item label="班会主题">
            <el-input v-model="form.theme" placeholder="例如：期中复盘与目标重建" />
          </el-form-item>
          <el-form-item label="适用年级">
            <el-select v-model="form.grade" class="full-width">
              <el-option v-for="item in gradeOptions" :key="item" :label="item" :value="item" />
            </el-select>
          </el-form-item>
          <el-form-item label="活动时长">
            <el-input-number v-model="form.duration" :min="20" :max="180" :step="5" />
          </el-form-item>
          <el-form-item label="参与对象">
            <el-input v-model="form.participants" placeholder="例如：全班学生、班干部、家委会成员" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleGenerate">生成方案</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <AiOutputPanel
        title="策划方案"
        subtitle="建议直接复制后再按本班情况做微调。"
        :content="result?.plan || ''"
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
import { planMeeting } from '@/api/aiTools'
import { getAiHistoryDetail } from '@/api/aiHistory'
import { downloadWordDocument } from '@/utils/export'

const gradeOptions = ['小学低段', '小学高段', '初一', '初二', '初三', '高一', '高二', '高三']
const route = useRoute()

const form = reactive({
  theme: '',
  grade: '高一',
  duration: 45,
  participants: '全班学生'
})

const { loading, error, result, generate } = useAiGenerate(planMeeting)

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
  if (!form.theme) {
    ElMessage.warning('请先填写班会主题')
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
  result.value = { plan: detail.content }
}

function handleDownload() {
  downloadWordDocument('班会活动策划', result.value?.plan || '', '班会活动策划.doc')
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
