<template>
  <div class="page-container ai-page">
    <div class="ai-layout">
      <el-card shadow="never">
        <template #header>
          <div>
            <div class="card-title">公告润色助手</div>
            <div class="card-desc">把老师的草稿快速整理成更正式、更清晰的通知文本。</div>
          </div>
        </template>

        <el-form :model="form" label-width="90px">
          <el-form-item label="原始内容">
            <el-input v-model="form.content" type="textarea" :rows="8" placeholder="请输入公告草稿" />
          </el-form-item>
          <el-form-item label="风格">
            <el-select v-model="form.style" class="full-width">
              <el-option label="正式" value="正式" />
              <el-option label="亲切" value="亲切" />
              <el-option label="简洁" value="简洁" />
            </el-select>
          </el-form-item>
          <el-form-item label="场景">
            <el-select v-model="form.scene" class="full-width">
              <el-option label="家长群" value="家长群" />
              <el-option label="班级群" value="班级群" />
              <el-option label="学校公告栏" value="学校公告栏" />
            </el-select>
          </el-form-item>
          <el-form-item label="关联班级">
            <el-select v-model="form.class_id" clearable class="full-width" placeholder="可选">
              <el-option v-for="item in classOptions" :key="item.id" :label="item.name" :value="item.id" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="loading" @click="handleGenerate">生成公告</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <AiOutputPanel
        title="润色结果"
        subtitle="适合直接复制到群通知、班级公告或学校公示。"
        :content="result?.polished || ''"
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
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiOutputPanel from '@/components/ai/AiOutputPanel.vue'
import { useAiGenerate } from '@/composables/useAiGenerate'
import { polishNotice } from '@/api/aiTools'
import { getClassList } from '@/api/class_'
import { getAiHistoryDetail } from '@/api/aiHistory'
import { downloadWordDocument } from '@/utils/export'

const route = useRoute()

const classOptions = ref([])
const form = reactive({
  content: '',
  style: '正式',
  scene: '家长群',
  class_id: ''
})

const { loading, error, result, generate } = useAiGenerate(polishNotice)

onMounted(async () => {
  await fetchClasses()
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

async function fetchClasses() {
  const res = await getClassList({ page: 1, page_size: 100 })
  classOptions.value = res.list
}

async function handleGenerate() {
  if (!form.content) {
    ElMessage.warning('请先输入公告草稿')
    return
  }

  await generate({
    ...form,
    class_id: form.class_id || undefined
  })
}

async function loadHistory(historyId) {
  if (!historyId) {
    return
  }

  const detail = await getAiHistoryDetail(Number(historyId))
  Object.assign(form, detail.input_params || {})
  result.value = { polished: detail.content }
}

function handleDownload() {
  downloadWordDocument('公告润色结果', result.value?.polished || '', '公告润色结果.doc')
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
