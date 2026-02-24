import { supabase } from './supabase'

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function getAuthHeaders(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  }
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }
  return headers
}

async function getAuthHeadersWithoutContentType(): Promise<HeadersInit> {
  const { data: { session } } = await supabase.auth.getSession()
  const headers: HeadersInit = {}
  if (session?.access_token) {
    headers['Authorization'] = `Bearer ${session.access_token}`
  }
  return headers
}

export const chatAPI = {
  sendMessage: async (message: string, conversationId?: string, stream: boolean = true) => {
    const headers = await getAuthHeaders()
    return fetch(`${API_BASE}/api/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        stream
      })
    })
  }
}

export const uploadDocument = async (file: File) => {
  const headers = await getAuthHeadersWithoutContentType()
  const formData = new FormData()
  formData.append('file', file)
  
  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    headers,
    body: formData
  })
  
  if (!response.ok) throw new Error('Upload failed')
  return response.json()
}

export const fetchWithAuth = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const headers = await getAuthHeaders()
  return fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
  })
}
