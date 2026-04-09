<template>
  <el-card shadow="never" class="ai-output-panel">
    <template #header>
      <div class="panel-header">
        <div>
          <div class="panel-title">{{ title }}</div>
          <div v-if="subtitle" class="panel-subtitle">{{ subtitle }}</div>
        </div>
        <div v-if="hasContent && !loading" class="panel-actions">
          <el-button link type="primary" @click="handleCopy">复制</el-button>
          <el-button v-if="showDownload" link type="success" @click="$emit('download')">下载</el-button>
        </div>
      </div>
    </template>

    <div v-if="loading" class="panel-state panel-loading">
      <el-skeleton :rows="5" animated />
      <div class="state-text">AI 正在整理内容，请稍候...</div>
    </div>

    <div v-else-if="error" class="panel-state panel-error">
      <el-result icon="error" :title="error" sub-title="可以直接重试，或者先调整输入条件。">
        <template #extra>
          <el-button type="primary" @click="$emit('retry')">重试</el-button>
        </template>
      </el-result>
    </div>

    <div v-else-if="hasContent" class="panel-content">
      <slot>
        <pre class="content-text">{{ content }}</pre>
      </slot>
    </div>

    <el-empty v-else description="填写左侧信息后即可生成结果" />
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  title: {
    type: String,
    default: 'AI 输出结果'
  },
  subtitle: {
    type: String,
    default: ''
  },
  content: {
    type: [String, Number],
    default: ''
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  },
  showDownload: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['retry', 'copy', 'download'])

const hasContent = computed(() => {
  if (typeof props.content === 'number') {
    return true
  }
  return !!String(props.content || '').trim()
})

async function handleCopy() {
  if (!hasContent.value) {
    return
  }

  await navigator.clipboard.writeText(String(props.content))
  ElMessage.success('内容已复制')
  emit('copy')
}
</script>

<style scoped lang="scss">
.ai-output-panel {
  height: 100%;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.panel-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.panel-actions {
  display: flex;
  gap: 8px;
}

.panel-state {
  min-height: 280px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.panel-loading {
  gap: 16px;
}

.state-text {
  font-size: 13px;
  color: #6b7280;
}

.panel-content {
  min-height: 280px;
}

.content-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  font-size: 14px;
  color: #1f2937;
  font-family: inherit;
}
</style>
