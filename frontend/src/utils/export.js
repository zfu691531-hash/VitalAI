function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  window.URL.revokeObjectURL(url)
}

export function downloadWordDocument(title, content, filename = 'AI结果.doc') {
  const body = Array.isArray(content) ? content.join('\n\n') : String(content || '')
  const html = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>${escapeHtml(title)}</title>
    <style>
      body {
        font-family: "Microsoft YaHei", "PingFang SC", Arial, sans-serif;
        line-height: 1.8;
        color: #1f2937;
        padding: 24px;
      }
      h1 {
        font-size: 20px;
        margin-bottom: 16px;
      }
      .content {
        white-space: pre-wrap;
        word-break: break-word;
        font-size: 14px;
      }
    </style>
  </head>
  <body>
    <h1>${escapeHtml(title)}</h1>
    <div class="content">${escapeHtml(body)}</div>
  </body>
</html>`

  const blob = new Blob([`\ufeff${html}`], {
    type: 'application/msword;charset=utf-8'
  })
  downloadBlob(blob, filename)
}

export function formatChatTranscript(messages, labels = {}) {
  const userLabel = labels.user || '我'
  const assistantLabel = labels.assistant || 'AI'

  return messages
    .map((message) => `${message.role === 'user' ? userLabel : assistantLabel}：\n${message.content}`)
    .join('\n\n')
}
