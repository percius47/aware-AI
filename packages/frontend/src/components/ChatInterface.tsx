'use client'

import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import { Send, Loader2, Plus, FileText, Brain, Wrench, CheckCircle, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react'
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

interface ThinkingStep {
  type: 'thinking' | 'intent' | 'tool_call' | 'tool_result'
  content: string
  timestamp: string
}

interface ClarificationRequest {
  message: string
  options: string[]
}

interface AgentEvent {
  type: 'thinking' | 'intent' | 'tool_call' | 'tool_result' | 'clarification' | 'chunk' | 'done' | 'error'
  content?: string
  tool?: string
  params?: Record<string, any>
  summary?: string
  message?: string
  options?: string[]
  intent?: string
  confidence?: number
  conversation_id?: string
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
  const [thinkingSteps, setThinkingSteps] = useState<ThinkingStep[]>([])
  const [clarificationRequest, setClarificationRequest] = useState<ClarificationRequest | null>(null)
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
    setThinkingSteps([])
    setClarificationRequest(null)

    try {
      const currentConvId = conversationId || undefined
      log('CHAT', 'Calling chatAPI.sendMessage...')
      const response = await chatAPI.sendMessage(input, currentConvId, true)

      log('CHAT', `Response received:`, { status: response.status, ok: response.ok })

      if (response) {
        // Handle streaming response with new agent event format
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
                    const event: AgentEvent = JSON.parse(line.slice(6))
                    
                    // Handle different event types
                    switch (event.type) {
                      case 'thinking':
                        log('AGENT', `Thinking: ${event.content}`)
                        setThinkingSteps(prev => [...prev, {
                          type: 'thinking',
                          content: event.content || '',
                          timestamp: new Date().toISOString()
                        }])
                        break
                      
                      case 'intent':
                        log('AGENT', `Intent: ${event.intent} (confidence: ${event.confidence})`)
                        setThinkingSteps(prev => [...prev, {
                          type: 'intent',
                          content: `Detected intent: ${event.intent} (${Math.round((event.confidence || 0) * 100)}% confident)`,
                          timestamp: new Date().toISOString()
                        }])
                        break
                      
                      case 'tool_call':
                        log('AGENT', `Tool call: ${event.tool}`, event.params)
                        setThinkingSteps(prev => [...prev, {
                          type: 'tool_call',
                          content: `Using tool: ${event.tool}`,
                          timestamp: new Date().toISOString()
                        }])
                        break
                      
                      case 'tool_result':
                        log('AGENT', `Tool result: ${event.tool} - ${event.summary}`)
                        setThinkingSteps(prev => [...prev, {
                          type: 'tool_result',
                          content: event.summary || `${event.tool} completed`,
                          timestamp: new Date().toISOString()
                        }])
                        break
                      
                      case 'clarification':
                        log('AGENT', `Clarification needed: ${event.message}`)
                        setClarificationRequest({
                          message: event.message || 'Could you clarify?',
                          options: event.options || []
                        })
                        streamComplete = true
                        break
                      
                      case 'chunk':
                        // Response content chunk
                        if (event.content) {
                          chunkCount++
                          fullResponse += event.content
                          setStreamingMessage(fullResponse)
                          if (chunkCount <= 3 || chunkCount % 10 === 0) {
                            log('STREAM', `Chunk #${chunkCount}: "${event.content.substring(0, 30)}..."`)
                          }
                        }
                        break
                      
                      case 'done':
                        log('STREAM', `Stream complete! Total chunks: ${chunkCount}`)
                        log('STREAM', `Response length: ${fullResponse.length} chars`)
                        log('STREAM', `Conversation ID: ${event.conversation_id}`)
                        
                        if (fullResponse) {
                          setMessages(prev => [...prev, {
                            role: 'assistant',
                            content: fullResponse,
                            timestamp: new Date().toISOString()
                          }])
                        }
                        setStreamingMessage('')
                        setThinkingSteps([])
                        
                        if (event.conversation_id) {
                          onConversationChange(event.conversation_id)
                        }
                        onMessageSent?.()
                        streamComplete = true
                        break
                      
                      case 'error':
                        log('AGENT', `Error: ${event.content}`)
                        toast.error(event.content || 'An error occurred')
                        streamComplete = true
                        break
                      
                      default:
                        // Legacy format support (chunk without type)
                        if ('chunk' in event && (event as any).chunk) {
                          chunkCount++
                          fullResponse += (event as any).chunk
                          setStreamingMessage(fullResponse)
                        }
                        if ('done' in event && (event as any).done) {
                          if (fullResponse) {
                            setMessages(prev => [...prev, {
                              role: 'assistant',
                              content: fullResponse,
                              timestamp: new Date().toISOString()
                            }])
                          }
                          setStreamingMessage('')
                          setThinkingSteps([])
                          if ((event as any).conversation_id) {
                            onConversationChange((event as any).conversation_id)
                          }
                          onMessageSent?.()
                          streamComplete = true
                        }
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

  // Handle clarification option selection
  const handleClarificationSelect = (option: string) => {
    setClarificationRequest(null)
    setInput(option)
    // Auto-send the clarification
    setTimeout(() => {
      const textarea = inputRef.current
      if (textarea) {
        textarea.value = option
        setInput(option)
      }
    }, 100)
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
        
        {/* Show thinking steps when agent is processing */}
        {thinkingSteps.length > 0 && (
          <ThinkingDisplay steps={thinkingSteps} isComplete={!isLoading || !!streamingMessage} />
        )}
        
        {/* Show clarification request if needed */}
        {clarificationRequest && (
          <ClarificationRequestUI 
            request={clarificationRequest} 
            onSelect={handleClarificationSelect} 
          />
        )}
        
        {/* Show typing indicator when loading but no streaming content yet */}
        {isLoading && !streamingMessage && thinkingSteps.length === 0 && (
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
        
        {/* Keyboard shortcuts hint */}
        <div className="flex items-center justify-center gap-4 mt-2 text-xs text-gray-400 dark:text-gray-500">
          <div className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 font-mono">Ctrl + K</kbd>
            <span>New chat</span>
          </div>
          <span className="text-gray-300 dark:text-gray-600">|</span>
          <div className="flex items-center gap-1">
            <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 font-mono">Ctrl + /</kbd>
            <span>Focus input</span>
          </div>
        
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

// Inline ThinkingDisplay component
function ThinkingDisplay({ steps, isComplete }: { steps: ThinkingStep[], isComplete: boolean }) {
  const [isExpanded, setIsExpanded] = useState(true)
  
  // Auto-collapse when complete
  useEffect(() => {
    if (isComplete) {
      const timer = setTimeout(() => setIsExpanded(false), 1000)
      return () => clearTimeout(timer)
    }
  }, [isComplete])
  
  const getIcon = (type: ThinkingStep['type']) => {
    switch (type) {
      case 'thinking':
        return <Brain className="w-4 h-4 text-purple-500" />
      case 'intent':
        return <HelpCircle className="w-4 h-4 text-blue-500" />
      case 'tool_call':
        return <Wrench className="w-4 h-4 text-orange-500" />
      case 'tool_result':
        return <CheckCircle className="w-4 h-4 text-green-500" />
      default:
        return <Brain className="w-4 h-4 text-gray-500" />
    }
  }
  
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%] bg-gray-50 dark:bg-gray-800/50 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
        <button 
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full px-4 py-2 flex items-center justify-between gap-2 text-sm text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-500 animate-pulse" />
            <span>Agent thinking...</span>
            <span className="text-xs text-gray-400">({steps.length} steps)</span>
          </div>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        
        {isExpanded && (
          <div className="px-4 pb-3 space-y-2 border-t border-gray-200 dark:border-gray-700 pt-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm animate-fadeIn">
                {getIcon(step.type)}
                <span className="text-gray-700 dark:text-gray-300">{step.content}</span>
              </div>
            ))}
            {!isComplete && (
              <div className="flex items-center gap-2 text-sm text-gray-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Processing...</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// Inline ClarificationRequest component
function ClarificationRequestUI({ 
  request, 
  onSelect 
}: { 
  request: ClarificationRequest, 
  onSelect: (option: string) => void 
}) {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[85%] bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800 p-4">
        <div className="flex items-start gap-2 mb-3">
          <HelpCircle className="w-5 h-5 text-amber-600 dark:text-amber-500 flex-shrink-0 mt-0.5" />
          <p className="text-gray-800 dark:text-gray-200">{request.message}</p>
        </div>
        
        {request.options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {request.options.map((option, idx) => (
              <button
                key={idx}
                onClick={() => onSelect(option)}
                className="px-3 py-1.5 text-sm bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors text-gray-700 dark:text-gray-300"
              >
                {option}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
