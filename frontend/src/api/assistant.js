import request from './request'
import { getToken } from '@/utils/auth'

export function getAssistantSession() {
  return request({
    url: '/assistant/session',
    method: 'get'
  })
}

export function createAssistantSession(data) {
  return request({
    url: '/assistant/session',
    method: 'post',
    data
  })
}

export function clearAssistantSession(data = {}) {
  return request({
    url: '/assistant/session/clear',
    method: 'post',
    data
  })
}

export function sendAssistantMessage(data) {
  return request({
    url: '/assistant/message',
    method: 'post',
    data
  })
}

export async function streamAssistantMessage(data, handlers = {}) {
  const token = getToken()
  const response = await fetch('/api/assistant/message/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data)
  })

  if (!response.ok || !response.body) {
    const text = await response.text()
    throw new Error(text || '个人 AI 助手暂时不可用')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() || ''

    for (const block of parts) {
      const line = block
        .split('\n')
        .find((item) => item.startsWith('data: '))
      if (!line) continue

      const payload = JSON.parse(line.slice(6))
      handlers.onEvent?.(payload)
    }
  }

  if (buffer.trim()) {
    const line = buffer
      .split('\n')
      .find((item) => item.startsWith('data: '))
    if (line) {
      handlers.onEvent?.(JSON.parse(line.slice(6)))
    }
  }
}
