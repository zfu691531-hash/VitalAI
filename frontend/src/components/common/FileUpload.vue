<template>
  <div class="file-upload">
    <el-upload
      ref="uploadRef"
      :action="action"
      :accept="accept"
      :limit="1"
      :auto-upload="false"
      :show-file-list="false"
      :on-change="handleFileChange"
      :on-exceed="handleExceed"
    >
      <template #trigger>
        <el-button type="primary">
          <el-icon><Upload /></el-icon>
          {{ buttonText }}
        </el-button>
      </template>
    </el-upload>

    <el-button
      v-if="templateUrl || templateAction"
      type="primary"
      link
      @click="downloadTemplate"
    >
      <el-icon><Download /></el-icon>
      下载模板
    </el-button>

    <div v-if="selectedFile" class="selected-file">
      <el-icon><Document /></el-icon>
      <span class="file-name">{{ selectedFile.name }}</span>
      <el-icon class="remove-icon" @click="removeFile"><Close /></el-icon>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Close, Document, Download, Upload } from '@element-plus/icons-vue'

const props = defineProps({
  action: {
    type: String,
    default: '#'
  },
  accept: {
    type: String,
    default: '.xlsx,.xls'
  },
  maxSize: {
    type: Number,
    default: 5
  },
  templateUrl: {
    type: String,
    default: ''
  },
  templateAction: {
    type: Function,
    default: null
  },
  buttonText: {
    type: String,
    default: '选择文件'
  }
})

const emit = defineEmits(['success', 'error', 'change'])

const uploadRef = ref(null)
const selectedFile = ref(null)

function handleFileChange(file) {
  const fileName = file.name.toLowerCase()
  const isValidType = props.accept.split(',').some((ext) => fileName.endsWith(ext.trim()))
  if (!isValidType) {
    ElMessage.error(`只支持 ${props.accept} 格式的文件`)
    return false
  }

  const isValidSize = file.size / 1024 / 1024 < props.maxSize
  if (!isValidSize) {
    ElMessage.error(`文件大小不能超过 ${props.maxSize}MB`)
    return false
  }

  selectedFile.value = file.raw
  emit('change', file.raw)
  emit('success', file.raw)
}

function handleExceed() {
  ElMessage.warning('只能选择一个文件，请先移除已选文件')
}

function removeFile() {
  selectedFile.value = null
  uploadRef.value?.clearFiles()
  emit('change', null)
}

async function downloadTemplate() {
  if (props.templateAction) {
    try {
      await props.templateAction()
    } catch {
      ElMessage.error('模板下载失败')
    }
  } else if (props.templateUrl) {
    window.open(props.templateUrl, '_blank')
  }
}

defineExpose({
  clearFiles: () => {
    selectedFile.value = null
    uploadRef.value?.clearFiles()
  }
})
</script>

<style scoped lang="scss">
.file-upload {
  display: inline-flex;
  align-items: center;
  gap: 12px;

  .selected-file {
    display: flex;
    align-items: center;
    padding: 4px 8px;
    background-color: #f0f9eb;
    border-radius: 4px;
    font-size: 13px;

    .file-name {
      margin: 0 8px;
      color: #67c23a;
    }

    .remove-icon {
      cursor: pointer;
      color: #909399;

      &:hover {
        color: #f56c6c;
      }
    }
  }
}
</style>
