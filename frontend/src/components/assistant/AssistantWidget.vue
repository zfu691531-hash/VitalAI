<template>
  <div class="assistant-widget" :style="widgetStyle">
    <transition name="assistant-panel">
      <div v-if="open" class="assistant-panel" :class="`role-${userStore.role}`">
        <div
          class="assistant-header"
          @pointerdown="startDrag"
        >
          <div class="assistant-header-copy">
            <span class="assistant-badge">{{ roleAssistant.badge }}</span>
            <div class="assistant-title">{{ title }}</div>
            <div class="assistant-subtitle">{{ subtitle }}</div>
          </div>
          <div class="header-actions">
            <button type="button" class="ghost-btn" :disabled="loading" @click.stop="handleClearHistory">
              清空记录
            </button>
            <button type="button" class="icon-btn" @click.stop="open = false">×</button>
          </div>
        </div>

        <div ref="messageListRef" class="assistant-messages">
          <div
            v-for="item in messages"
            :key="item.id || `${item.role}-${item.content}`"
            class="message-row"
            :class="item.role"
          >
            <div class="message-bubble">
              {{ item.renderedContent || item.content }}
            </div>
          </div>

          <div v-if="loading && !statusText" class="message-row assistant">
            <div class="message-bubble">正在思考中...</div>
          </div>

          <div v-if="statusText" class="assistant-status">
            <span class="status-dot"></span>
            {{ statusText }}
          </div>
        </div>

        <div class="assistant-footer">
          <el-input
            v-model="inputValue"
            type="textarea"
            :rows="2"
            resize="none"
            :placeholder="roleAssistant.placeholder"
            @keydown.enter.prevent="handleSubmit"
          />
          <div class="footer-actions">
            <span class="memory-tip">已启用会话记忆</span>
            <el-button type="primary" :loading="loading" @click="handleSubmit">发送</el-button>
          </div>
        </div>
      </div>
    </transition>

    <div class="assistant-entry">
      <div v-if="!open" class="assistant-callout" @click="toggleOpen">
        <div class="callout-badge">{{ roleAssistant.badge }}</div>
        <div class="callout-text">
          <div class="callout-title">{{ roleAssistant.fabLabel }}</div>
          <div class="callout-subtitle">{{ roleAssistant.fabHint }}</div>
        </div>
      </div>

      <button
        type="button"
        class="assistant-fab"
        :class="`role-${userStore.role}`"
        @click="toggleOpen"
        @pointerdown="startFabDrag"
      >
        <span class="fab-ring"></span>
        <span class="fab-core">{{ fabText }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { clearAssistantSession, getAssistantSession, streamAssistantMessage } from '@/api/assistant'
import { useUserStore } from '@/stores/user'
import { getRoleUi } from '@/utils/role-ui'

const userStore = useUserStore()

const open = ref(false)
const loading = ref(false)
const inputValue = ref('')
const sessionId = ref(null)
const messages = ref([])
const messageListRef = ref(null)
const statusText = ref('')
const position = ref({ x: 0, y: 0 })

const dragState = {
  active: false,
  startX: 0,
  startY: 0,
  initialX: 0,
  initialY: 0
}

const roleUi = computed(() => getRoleUi(userStore.role))
const roleAssistant = computed(() => roleUi.value.assistant || {})

const title = computed(() => roleAssistant.value.panelTitle || `${userStore.name || userStore.username || '当前用户'}的 AI 助手`)
const subtitle = computed(() => roleAssistant.value.panelSubtitle || '随时问我校园与日常问题')
const fabText = computed(() => {
  if (userStore.role === 'student') return '陪你'
  if (userStore.role === 'teacher') return '助教'
  return '校务'
})

const assistantVars = computed(() => ({
  '--assistant-shell': roleAssistant.value.shell,
  '--assistant-header': roleAssistant.value.header,
  '--assistant-message-bg': roleAssistant.value.messageBg,
  '--assistant-accent': roleAssistant.value.accent,
  '--assistant-accent-secondary': roleAssistant.value.accentSecondary,
  '--assistant-accent-soft': roleAssistant.value.accentSoft,
  '--assistant-user-bubble': roleAssistant.value.userBubble,
  '--assistant-bot-bubble': roleAssistant.value.assistantBubble,
  '--assistant-status-bg': roleAssistant.value.statusBg,
  '--assistant-status-text': roleAssistant.value.statusText,
  '--assistant-fab-shadow': roleAssistant.value.fabShadow
}))

const widgetStyle = computed(() => ({
  ...assistantVars.value,
  transform: `translate(${position.value.x}px, ${position.value.y}px)`
}))

onMounted(async () => {
  if (!userStore.isLoggedIn) return
  await hydrateSession()
})

onBeforeUnmount(() => {
  stopDrag()
})

async function hydrateSession() {
  try {
    const session = await getAssistantSession()
    sessionId.value = session.session_id

    const remoteMessages = (session.messages || []).map((item) => ({
      ...item,
      role: item.role || item.message_role,
      renderedContent: item.content
    }))

    if (!remoteMessages.length && session.greeting) {
      messages.value = [
        {
          role: 'assistant',
          content: session.greeting,
          renderedContent: session.greeting
        }
      ]
    } else {
      messages.value = remoteMessages
    }

    await scrollToBottom()
  } catch (error) {
    // 静默失败，避免阻塞主界面
  }
}

function toggleOpen() {
  open.value = !open.value
  nextTick(() => scrollToBottom())
}

async function handleClearHistory() {
  if (loading.value) return

  try {
    await ElMessageBox.confirm('清空当前会话记录后无法恢复，是否继续？', '清空记录', {
      confirmButtonText: '确认清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch {
    return
  }

  try {
    const result = await clearAssistantSession({ session_id: sessionId.value })
    sessionId.value = result.session_id || sessionId.value
    messages.value = result.greeting
      ? [{ role: 'assistant', content: result.greeting, renderedContent: result.greeting }]
      : []
    statusText.value = ''
    inputValue.value = ''
    ElMessage.success(result.msg || '已清空当前会话记录')
    await scrollToBottom()
  } catch (error) {
    ElMessage.error(error.message || '清空记录失败，请稍后再试')
  }
}

async function handleSubmit() {
  const content = inputValue.value.trim()
  if (!content || loading.value) return

  messages.value.push({
    id: `user-${Date.now()}`,
    role: 'user',
    content,
    renderedContent: content
  })

  inputValue.value = ''
  loading.value = true
  statusText.value = ''
  await scrollToBottom()

  const assistantMessage = {
    id: `assistant-${Date.now()}`,
    role: 'assistant',
    content: '',
    renderedContent: ''
  }
  messages.value.push(assistantMessage)

  try {
    await streamAssistantMessage(
      {
        session_id: sessionId.value,
        content
      },
      {
        onEvent(payload) {
          if (payload.type === 'status') {
            statusText.value = payload.message || ''
            scrollToBottom()
            return
          }

          if (payload.type === 'start') {
            sessionId.value = payload.session_id || sessionId.value
            if (payload.message_id) assistantMessage.id = payload.message_id
            return
          }

          if (payload.type === 'chunk') {
            assistantMessage.renderedContent += payload.content || ''
            assistantMessage.content = assistantMessage.renderedContent
            scrollToBottom()
            return
          }

          if (payload.type === 'done' && payload.message) {
            sessionId.value = payload.session_id || sessionId.value
            assistantMessage.id = payload.message.id || assistantMessage.id
            assistantMessage.content = payload.message.content || assistantMessage.content
            assistantMessage.renderedContent = payload.message.content || assistantMessage.renderedContent
            statusText.value = ''
          }
        }
      }
    )
  } catch (error) {
    messages.value = messages.value.filter((item) => item !== assistantMessage)
    statusText.value = ''
    ElMessage.error(error.message || '个人 AI 助手暂时不可用')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

function startDrag(event) {
  dragState.active = true
  dragState.startX = event.clientX
  dragState.startY = event.clientY
  dragState.initialX = position.value.x
  dragState.initialY = position.value.y
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', stopDrag)
}

function startFabDrag(event) {
  if (open.value) return
  startDrag(event)
}

function onDragMove(event) {
  if (!dragState.active) return
  const nextX = dragState.initialX + (event.clientX - dragState.startX)
  const nextY = dragState.initialY + (event.clientY - dragState.startY)
  position.value = clampPosition(nextX, nextY)
}

function stopDrag() {
  dragState.active = false
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', stopDrag)
}

function clampPosition(x, y) {
  const maxX = Math.max(window.innerWidth * 0.35, 140)
  const minX = -Math.max(window.innerWidth * 0.55, 220)
  const maxY = Math.max(window.innerHeight * 0.3, 120)
  const minY = -Math.max(window.innerHeight * 0.6, 320)
  return {
    x: Math.min(Math.max(x, minX), maxX),
    y: Math.min(Math.max(y, minY), maxY)
  }
}

async function scrollToBottom() {
  await nextTick()
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}
</script>

<style scoped lang="scss">
.assistant-widget {
  position: fixed;
  right: 20px;
  bottom: 20px;
  z-index: 60;
  will-change: transform;
  --assistant-shell: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(247, 250, 255, 0.99) 100%);
  --assistant-header: linear-gradient(135deg, #eef6ff 0%, #f8fafc 100%);
  --assistant-message-bg: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  --assistant-accent: #1d4ed8;
  --assistant-accent-secondary: #38bdf8;
  --assistant-accent-soft: rgba(29, 78, 216, 0.12);
  --assistant-user-bubble: linear-gradient(135deg, #1d4ed8 0%, #38bdf8 100%);
  --assistant-bot-bubble: #eef4ff;
  --assistant-status-bg: rgba(29, 78, 216, 0.08);
  --assistant-status-text: #32517a;
  --assistant-fab-shadow: 0 22px 44px rgba(29, 78, 216, 0.3);
}

.assistant-entry {
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  gap: 12px;
}

.assistant-callout {
  max-width: 200px;
  padding: 12px 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--assistant-accent-soft);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(14px);
  cursor: pointer;
  animation: float-in 2.6s ease-in-out infinite;
}

.callout-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--assistant-accent-soft);
  color: var(--assistant-status-text);
  font-size: 11px;
  font-weight: 700;
}

.callout-text {
  margin-top: 8px;
}

.callout-title {
  font-size: 14px;
  font-weight: 700;
  color: #182433;
}

.callout-subtitle {
  margin-top: 4px;
  font-size: 12px;
  line-height: 1.5;
  color: #617289;
}

.assistant-fab {
  position: relative;
  width: 76px;
  height: 76px;
  border: none;
  border-radius: 28px;
  background: linear-gradient(135deg, var(--assistant-accent) 0%, var(--assistant-accent-secondary) 100%);
  color: #fff;
  box-shadow: var(--assistant-fab-shadow);
  cursor: grab;
  overflow: hidden;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.assistant-fab:active {
  cursor: grabbing;
}

.assistant-fab:hover {
  transform: translateY(-2px) scale(1.02);
}

.fab-ring {
  position: absolute;
  inset: 8px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.34);
}

.fab-core {
  position: relative;
  z-index: 1;
  font-size: 16px;
  font-weight: 800;
  letter-spacing: 0.08em;
}

.assistant-panel {
  width: min(400px, calc(100vw - 28px));
  height: min(640px, calc(100vh - 120px));
  margin-bottom: 14px;
  display: flex;
  flex-direction: column;
  border-radius: 28px;
  overflow: hidden;
  background: var(--assistant-shell);
  box-shadow: 0 26px 60px rgba(15, 23, 42, 0.24);
  backdrop-filter: blur(18px);
}

.assistant-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 20px 16px;
  background: var(--assistant-header);
  border-bottom: 1px solid var(--assistant-accent-soft);
  cursor: grab;
  user-select: none;
}

.assistant-header:active {
  cursor: grabbing;
}

.assistant-header-copy {
  min-width: 0;
}

.assistant-badge {
  display: inline-flex;
  align-items: center;
  padding: 5px 10px;
  border-radius: 999px;
  background: var(--assistant-accent-soft);
  color: var(--assistant-status-text);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.assistant-title {
  margin-top: 10px;
  font-size: 17px;
  font-weight: 800;
  line-height: 1.35;
  color: #132235;
}

.assistant-subtitle {
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.6;
  color: #627389;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ghost-btn,
.icon-btn {
  border: none;
  cursor: pointer;
}

.ghost-btn {
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.78);
  color: #315273;
  font-size: 12px;
  font-weight: 700;
}

.ghost-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: rgba(15, 23, 42, 0.06);
  color: #0f172a;
  font-size: 20px;
  line-height: 1;
}

.assistant-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: var(--assistant-message-bg);
}

.message-row {
  display: flex;
  margin-bottom: 12px;
}

.message-row.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 86%;
  padding: 13px 15px;
  border-radius: 20px;
  white-space: pre-wrap;
  line-height: 1.72;
  font-size: 13px;
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.05);
}

.message-row.assistant .message-bubble {
  background: var(--assistant-bot-bubble);
  color: #203246;
}

.message-row.user .message-bubble {
  background: var(--assistant-user-bubble);
  color: #fff;
}

.assistant-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: var(--assistant-status-bg);
  color: var(--assistant-status-text);
  font-size: 12px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--assistant-accent);
  box-shadow: 0 0 0 4px rgba(29, 78, 216, 0.14);
}

.assistant-footer {
  padding: 16px 18px 18px;
  background: rgba(255, 255, 255, 0.9);
  border-top: 1px solid rgba(148, 163, 184, 0.14);
}

.footer-actions {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.memory-tip {
  font-size: 12px;
  color: #6b7c93;
}

.assistant-panel-enter-active,
.assistant-panel-leave-active {
  transition: all 0.22s ease;
}

.assistant-panel-enter-from,
.assistant-panel-leave-to {
  opacity: 0;
  transform: translateY(18px) scale(0.98);
}

@keyframes float-in {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@media (max-width: 768px) {
  .assistant-widget {
    right: 14px;
    bottom: 14px;
  }

  .assistant-callout {
    display: none;
  }

  .assistant-panel {
    width: min(360px, calc(100vw - 16px));
    height: min(72vh, calc(100vh - 90px));
  }
}
</style>
