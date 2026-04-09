<template>
  <el-card shadow="never" class="ai-chat-panel">
    <template #header>
      <div class="chat-header">
        <div>
          <div class="chat-title">{{ title }}</div>
          <div v-if="subtitle" class="chat-subtitle">{{ subtitle }}</div>
        </div>
        <div class="header-actions">
          <el-button v-if="showDownload && messages.length > 0" link type="success" @click="$emit('download')">
            下载 Word
          </el-button>
          <el-button link type="danger" @click="$emit('clear')">清空对话</el-button>
        </div>
      </div>
    </template>

    <div ref="messageContainerRef" class="message-container">
      <el-empty v-if="messages.length === 0" description="先发出第一条问题，AI 会在这里持续回答" />

      <div
        v-for="(message, index) in messages"
        :key="`${message.role}-${index}`"
        :class="['message-item', message.role]"
      >
        <div class="message-bubble">
          <div class="message-role">{{ message.role === 'user' ? userLabel : assistantLabel }}</div>
          <div class="message-content">{{ message.content }}</div>
        </div>
      </div>

      <div v-if="loading" class="message-item assistant">
        <div class="message-bubble loading-bubble">
          <div class="message-role">{{ assistantLabel }}</div>
          <div class="typing-dots">
            <span />
            <span />
            <span />
          </div>
        </div>
      </div>
    </div>

    <div class="input-area">
      <el-input
        v-model="draft"
        type="textarea"
        :rows="3"
        :placeholder="placeholder"
        resize="none"
        @keydown.ctrl.enter.prevent="handleSend"
      />
      <div class="input-footer">
        <span class="input-tip">支持 `Ctrl + Enter` 快速发送</span>
        <el-button type="primary" :loading="loading" @click="handleSend">发送</el-button>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: 'AI 对话'
  },
  subtitle: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '请输入内容'
  },
  userLabel: {
    type: String,
    default: '我'
  },
  assistantLabel: {
    type: String,
    default: 'AI'
  },
  showDownload: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send', 'clear', 'download'])

const draft = ref('')
const messageContainerRef = ref(null)

watch(
  () => [props.messages.length, props.loading],
  async () => {
    await nextTick()
    const container = messageContainerRef.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  },
  { deep: true }
)

function handleSend() {
  const value = draft.value.trim()
  if (!value || props.loading) {
    return
  }

  emit('send', value)
  draft.value = ''
}
</script>

<style scoped lang="scss">
.ai-chat-panel {
  display: flex;
  flex-direction: column;
  min-height: 620px;
}

.chat-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chat-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.chat-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: #6b7280;
}

.message-container {
  flex: 1;
  min-height: 420px;
  max-height: 420px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 0 12px;
}

.message-item {
  display: flex;
}

.message-item.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 82%;
  border-radius: 16px;
  padding: 14px 16px;
  background: #f3f4f6;
  color: #111827;
}

.message-item.user .message-bubble {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
}

.message-role {
  font-size: 12px;
  font-weight: 600;
  opacity: 0.8;
  margin-bottom: 6px;
}

.message-content {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.7;
}

.loading-bubble {
  min-width: 120px;
}

.typing-dots {
  display: flex;
  gap: 6px;
  align-items: center;
  min-height: 18px;
}

.typing-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9ca3af;
  animation: blink 1.2s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.15s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.3s;
}

.input-area {
  border-top: 1px solid #e5e7eb;
  padding-top: 16px;
}

.input-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.input-tip {
  font-size: 12px;
  color: #9ca3af;
}

@keyframes blink {
  0%,
  80%,
  100% {
    transform: scale(0.8);
    opacity: 0.5;
  }

  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
