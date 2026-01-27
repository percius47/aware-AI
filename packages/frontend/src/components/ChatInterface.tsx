'use client'

import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import { Send, Loader2, Plus, FileText, X } from 'lucide-react'
import { chatAPI, uploadDocument } from '@/lib/api'

// Console logging helper
const log = (category: string, message: string, data?: any) => {
  const timestamp = new Date().toLocaleTimeString()
  const prefix = `[${timestamp}] [${category}]`
  if (data !== undefined) {
    console.log(`${prefix} ${message}`, data)
  } else {
    console.log(`${prefix} ${message}`)
  }
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

interface ChatInterfaceProps {
  conversationId: string | null
  onConversationChange: (id: string | null) => void
  onMessageSent?: () => void  // Callback when a message is sent
  initialMessages?: Message[]  // Messages to load when switching threads
}

export default function ChatInterface({ 
  conversationId, 
  onConversationChange,
  onMessageSent,
  initialMessages = []
}: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [streamingMessage, setStreamingMessage] = useState('')
  const [showAttachMenu, setShowAttachMenu] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  // Load initial messages when switching threads
  useEffect(() => {
    setMessages(initialMessages)
  }, [initialMessages])

  useEffect(() => {
    scrollToBottom()
  }, [messages, streamingMessage])

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    log('CHAT', '════════════════════════════════════════')
    log('CHAT', 'User clicked send')
    log('CHAT', `Message: "${input}"`)
    log('CHAT', `Current conversation ID: ${conversationId || '(none - new chat)'}`)

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)
    setStreamingMessage('')

    try {
      const currentConvId = conversationId || undefined
      log('CHAT', 'Calling chatAPI.sendMessage...')
      const response = await chatAPI.sendMessage(input, currentConvId, true)

      log('CHAT', `Response received:`, { status: response.status, ok: response.ok })

      if (response) {
        // Handle streaming response
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
        let fullResponse = ''
        let streamComplete = false
        let chunkCount = 0

        if (reader) {
          log('STREAM', 'Starting to read response stream...')
          try {
            while (!streamComplete) {
              const { done, value } = await reader.read()
              if (done) {
                log('STREAM', 'Stream ended (done=true)')
                break
              }

              const chunk = decoder.decode(value)
              const lines = chunk.split('\n')

              for (const line of lines) {
                if (line.startsWith('data: ')) {
                  try {
                    const data = JSON.parse(line.slice(6))
                    if (data.chunk) {
                      chunkCount++
                      fullResponse += data.chunk
                      setStreamingMessage(fullResponse)
                      if (chunkCount <= 3 || chunkCount % 10 === 0) {
                        log('STREAM', `Chunk #${chunkCount}: "${data.chunk.substring(0, 30)}..."`)
                      }
                    }
                    if (data.done) {
                      log('STREAM', `Stream complete! Total chunks: ${chunkCount}`)
                      log('STREAM', `Response length: ${fullResponse.length} chars`)
                      log('STREAM', `New conversation ID: ${data.conversation_id}`)
                      // Stream is complete - add message and exit
                      setMessages(prev => [...prev, {
                        role: 'assistant',
                        content: fullResponse,
                        timestamp: new Date().toISOString()
                      }])
                      setStreamingMessage('')
                      if (data.conversation_id) {
                        onConversationChange(data.conversation_id)
                      }
                      // Notify parent that a message was sent
                      onMessageSent?.()
                      // Mark stream as complete and break out
                      streamComplete = true
                      break
                    }
                  } catch (e) {
                    // Skip invalid JSON
                  }
                }
              }
            }
          } finally {
            // Always cancel the reader to prevent hanging
            reader.cancel().catch(() => {})
          }
        } else {
          log('STREAM', 'ERROR: No reader available from response')
        }
      }
    } catch (error) {
      log('CHAT', 'ERROR occurred:', error)
      console.error('Chat error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }])
    } finally {
      log('CHAT', 'Request complete')
      log('CHAT', '════════════════════════════════════════')
      setIsLoading(false)
      setStreamingMessage('')
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setShowAttachMenu(false)
    setUploadStatus('Uploading...')

    try {
      const result = await uploadDocument(file)
      setUploadStatus(`Uploaded: ${result.chunks} chunks processed`)
      setTimeout(() => setUploadStatus(null), 3000)
    } catch (error) {
      setUploadStatus('Upload failed')
      setTimeout(() => setUploadStatus(null), 3000)
    }
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            Start a conversation! I remember our past interactions and can help you with questions.
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        
        {streamingMessage && (
          <MessageBubble 
            message={{
              role: 'assistant',
              content: streamingMessage,
              timestamp: new Date().toISOString()
            }}
            isStreaming
          />
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Upload status notification */}
      {uploadStatus && (
        <div className="px-4 py-2 bg-blue-50 text-blue-700 text-sm border-t">
          {uploadStatus}
        </div>
      )}

      <div className="border-t p-4">
        <div className="flex gap-2 items-center relative">
          {/* Hidden file input */}
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
          />
          
          {/* Attachment button */}
          <div className="relative">
            <button
              onClick={() => setShowAttachMenu(!showAttachMenu)}
              className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              title="Add attachment"
            >
              <Plus className="w-5 h-5" />
            </button>
            
            {/* Attachment menu dropdown */}
            {showAttachMenu && (
              <div className="absolute bottom-full left-0 mb-2 bg-white rounded-lg shadow-lg border py-1 min-w-[160px] z-10">
                <button
                  onClick={() => {
                    fileInputRef.current?.click()
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Upload Document
                </button>
              </div>
            )}
          </div>
          
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type your message..."
            className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 bg-white"
            disabled={isLoading}
          />
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
      
      {/* Click outside to close menu */}
      {showAttachMenu && (
        <div 
          className="fixed inset-0 z-0" 
          onClick={() => setShowAttachMenu(false)}
        />
      )}
    </div>
  )
}
