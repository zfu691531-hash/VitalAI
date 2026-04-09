<!--
  二次确认弹窗组件
  =================
  用于删除等危险操作的二次确认。
  - 显示操作描述文字（如"确认删除该学生信息？删除后不可恢复"）
  - 确认/取消按钮
  - 支持自定义确认按钮文字和类型（danger）
  props: { visible, title, message, confirmText, confirmType }
  emit: confirm, cancel
-->
<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @closed="handleClosed"
  >
    <div class="confirm-content">
      <el-icon class="confirm-icon" :class="iconClass">
        <WarningFilled v-if="confirmType === 'danger'" />
        <QuestionFilled v-else />
      </el-icon>
      <div class="confirm-message">
        <p class="message-text">{{ message }}</p>
        <p v-if="subMessage" class="sub-message">{{ subMessage }}</p>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleCancel">{{ cancelText }}</el-button>
      <el-button
        :type="confirmType"
        :loading="loading"
        @click="handleConfirm"
      >
        {{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '提示'
  },
  message: {
    type: String,
    default: '确定执行此操作？'
  },
  subMessage: {
    type: String,
    default: ''
  },
  confirmText: {
    type: String,
    default: '确定'
  },
  cancelText: {
    type: String,
    default: '取消'
  },
  confirmType: {
    type: String,
    default: 'primary' // primary / danger / warning
  },
  width: {
    type: String,
    default: '420px'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel'])

const dialogVisible = ref(props.visible)

// 监听props变化
watch(
  () => props.visible,
  (val) => {
    dialogVisible.value = val
  }
)

// 图标样式
const iconClass = computed(() => ({
  'icon-danger': props.confirmType === 'danger',
  'icon-warning': props.confirmType === 'warning'
}))

// 确认
function handleConfirm() {
  emit('confirm')
}

// 取消
function handleCancel() {
  dialogVisible.value = false
  emit('cancel')
}

// 关闭后
function handleClosed() {
  emit('update:visible', false)
}
</script>

<style scoped lang="scss">
.confirm-content {
  display: flex;
  align-items: flex-start;
  padding: 10px 0;

  .confirm-icon {
    font-size: 24px;
    margin-right: 16px;
    margin-top: 2px;

    &.icon-danger {
      color: #f56c6c;
    }

    &.icon-warning {
      color: #e6a23c;
    }
  }

  .confirm-message {
    flex: 1;

    .message-text {
      font-size: 16px;
      color: #303133;
      margin: 0;
      line-height: 1.5;
    }

    .sub-message {
      font-size: 14px;
      color: #909399;
      margin: 8px 0 0;
      line-height: 1.5;
    }
  }
}
</style>
