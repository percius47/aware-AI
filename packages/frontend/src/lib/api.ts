const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const chatAPI = {
  sendMessage: async (message: string, conversationId?: string, stream: boolean = true) => {
    return fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        stream
      })
    })
  }
}

export const uploadDocument = async (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData
  })
  
  if (!response.ok) throw new Error('Upload failed')
  return response.json()
}
