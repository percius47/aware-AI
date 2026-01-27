'use client'

import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import { Send, Loader2, Plus, FileText } from 'lucide-react'
import { chatAPI, uploadDocument } from '@/lib/api'
import toast from 'react-hot-toast'

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
  const [isUploading, setIsUploading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

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

  // Listen for focus input event from keyboard shortcuts
  useEffect(() => {
    const handleFocusInput = () => {
      inputRef.current?.focus()
    }
    
    window.addEventListener('focusChatInput', handleFocusInput)
    return () => window.removeEventListener('focusChatInput', handleFocusInput)
  }, [])

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
      toast.error('Failed to send message. Please try again.')
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
    setIsUploading(true)
    
    const uploadToast = toast.loading(`Uploading ${file.name}...`)

    try {
      const result = await uploadDocument(file)
      toast.success(
        `Document uploaded successfully! The assistant will now remember these details. (${result.chunks} chunks processed)`,
        { id: uploadToast, duration: 5000 }
      )
    } catch (error) {
      toast.error('Failed to upload document. Please try again.', { id: uploadToast })
    } finally {
      setIsUploading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 dark:text-gray-400 mt-8">
            <p className="text-lg mb-2">Start a conversation!</p>
            <p className="text-sm">I remember our past interactions and can help you with questions.</p>
            <p className="text-xs mt-4 text-gray-400 dark:text-gray-500">
              Tip: Upload documents to add them to my knowledge base.
            </p>
          </div>
        )}
        
        {messages.map((msg, idx) => (
          <MessageBubble key={idx} message={msg} />
        ))}
        
        {/* Show typing indicator when loading but no streaming content yet */}
        {isLoading && !streamingMessage && (
          <MessageBubble 
            message={{
              role: 'assistant',
              content: '',
              timestamp: new Date().toISOString()
            }}
            isTyping
          />
        )}
        
        {/* Show streaming message once content starts arriving */}
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

      <div className="border-t dark:border-gray-700 p-4 bg-white dark:bg-gray-800">
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
              disabled={isUploading}
              className="p-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
              title="Add attachment"
            >
              <Plus className="w-5 h-5" />
            </button>
            
            {/* Attachment menu dropdown */}
            {showAttachMenu && (
              <div className="absolute bottom-full left-0 mb-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 min-w-[160px] z-10">
                <button
                  onClick={() => {
                    fileInputRef.current?.click()
                  }}
                  className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                >
                  <FileText className="w-4 h-4" />
                  Upload Document
                </button>
              </div>
            )}
          </div>
          
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
                // Shift+Enter allows default behavior (new line)
              }}
              placeholder="Type your message..."
              className="w-full px-4 py-2 pr-16 border dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 text-gray-900 dark:text-white bg-white dark:bg-gray-700 placeholder-gray-400 dark:placeholder-gray-500 resize-none min-h-[42px] max-h-[120px]"
              disabled={isLoading}
              title="Focus with Ctrl+/"
              rows={1}
              style={{ height: 'auto', overflowY: input.includes('\n') ? 'auto' : 'hidden' }}
              onInput={(e) => {
                const target = e.target as HTMLTextAreaElement
                target.style.height = 'auto'
                target.style.height = Math.min(target.scrollHeight, 120) + 'px'
              }}
            />
            <kbd className="hidden md:flex items-center gap-0.5 absolute right-3 top-3 text-xs bg-gray-100 dark:bg-gray-600 px-1.5 py-0.5 rounded text-gray-400 dark:text-gray-400 pointer-events-none">⌘<span>+</span>/</kbd>
          </div>
          <button
            onClick={handleSend}
            disabled={isLoading || !input.trim()}
            className="px-4 md:px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 transition-colors"
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
