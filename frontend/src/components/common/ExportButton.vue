<template>
  <el-dropdown :disabled="loading" @command="handleExport">
    <el-button type="success" :loading="loading">
      <el-icon v-if="!loading"><Download /></el-icon>
      {{ loading ? '导出中...' : buttonText }}
      <el-icon class="el-icon--right"><ArrowDown /></el-icon>
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="format in availableFormats"
          :key="format.value"
          :command="format.value"
          :disabled="format.disabled"
        >
          <el-icon><component :is="format.icon" /></el-icon>
          {{ format.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown, Document, Download, Picture } from '@element-plus/icons-vue'

const props = defineProps({
  formats: {
    type: Array,
    default: () => ['excel']
  },
  buttonText: {
    type: String,
    default: '导出'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['export'])

const formatConfig = {
  excel: { label: '导出 Excel', icon: Document, disabled: false },
  word: { label: '导出 Word', icon: Document, disabled: false },
  image: { label: '导出图片', icon: Picture, disabled: false }
}

const availableFormats = computed(() =>
  props.formats.map((format) => ({
    value: format,
    ...formatConfig[format]
  }))
)

function handleExport(format) {
  emit('export', format)
}
</script>

<style scoped lang="scss">
.el-dropdown {
  margin-left: 12px;
}
</style>
