'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import ChatInterface from '@/components/ChatInterface'
import ThreadSidebar from '@/components/ThreadSidebar'
import { MessageSquare, Brain, FileText, Layers, Menu, Moon, Sun, Download } from 'lucide-react'
import { API_BASE } from '@/lib/api'
import { useTheme } from '@/components/ThemeProvider'
import toast from 'react-hot-toast'

interface SessionStats {
  session: {
    messages_sent: number
    active_threads: number
  }
  lifetime: {
    total_embeddings: number
    documents_uploaded: number
    total_threads: number
  }
  memory: {
    memories_created: number
    using_fallback: boolean
  }
}

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: string
}

export default function Home() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [stats, setStats] = useState<SessionStats | null>(null)
  const [messageCount, setMessageCount] = useState(0)
  const [sidebarRefresh, setSidebarRefresh] = useState(0)
  const [loadedMessages, setLoadedMessages] = useState<Message[]>([])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [showExportMenu, setShowExportMenu] = useState(false)
  const { theme, toggleTheme } = useTheme()
  const inputRef = useRef<HTMLInputElement>(null)

  // Fetch stats from backend
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/stats`)
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }, [])

  // Fetch stats on mount and after each message
  useEffect(() => {
    fetchStats()
  }, [fetchStats, messageCount])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K - New chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        handleNewChat()
        toast.success('New chat started', { duration: 2000 })
      }
      
      // Ctrl/Cmd + / - Focus input
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        // Dispatch custom event that ChatInterface listens to
        window.dispatchEvent(new CustomEvent('focusChatInput'))
      }
      
      // Escape - Close sidebar on mobile
      if (e.key === 'Escape' && sidebarOpen) {
        setSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sidebarOpen])

  // Callback when a message is sent
  const handleMessageSent = () => {
    setMessageCount(prev => prev + 1)
    // Refresh sidebar to show new/updated threads
    setSidebarRefresh(prev => prev + 1)
  }

  // Handle selecting a thread from sidebar
  const handleSelectThread = async (threadId: string | null) => {
    if (!threadId) {
      setConversationId(null)
      setLoadedMessages([])
      return
    }

    try {
      const response = await fetch(`${API_BASE}/api/threads/${threadId}`)
      if (response.ok) {
        const thread = await response.json()
        setConversationId(threadId)
        // Convert messages to the format ChatInterface expects
        const messages = (thread.messages || []).map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content,
          timestamp: m.created_at
        }))
        setLoadedMessages(messages)
      }
    } catch (error) {
      console.error('Failed to load thread:', error)
    }
  }

  // Handle new chat
  const handleNewChat = () => {
    setConversationId(null)
    setLoadedMessages([])
  }

  // Export conversation as JSON
  const exportAsJSON = () => {
    if (loadedMessages.length === 0) {
      toast.error('No messages to export')
      return
    }

    const data = {
      conversationId,
      exportedAt: new Date().toISOString(),
      messages: loadedMessages
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aware-ai-conversation-${conversationId?.slice(0, 8) || 'new'}.json`
    a.click()
    URL.revokeObjectURL(url)
    setShowExportMenu(false)
    toast.success('Conversation exported as JSON')
  }

  // Export conversation as Markdown
  const exportAsMarkdown = () => {
    if (loadedMessages.length === 0) {
      toast.error('No messages to export')
      return
    }

    let markdown = `# Aware AI Conversation\n\n`
    markdown += `**Exported:** ${new Date().toLocaleString()}\n\n---\n\n`
    
    loadedMessages.forEach(msg => {
      const role = msg.role === 'user' ? '**You:**' : '**Assistant:**'
      markdown += `${role}\n\n${msg.content}\n\n---\n\n`
    })

    const blob = new Blob([markdown], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `aware-ai-conversation-${conversationId?.slice(0, 8) || 'new'}.md`
    a.click()
    URL.revokeObjectURL(url)
    setShowExportMenu(false)
    toast.success('Conversation exported as Markdown')
  }

  return (
    <main className="h-screen flex bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      {/* Sidebar */}
      <ThreadSidebar
        currentThreadId={conversationId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        refreshTrigger={sidebarRefresh}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        stats={stats}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with stats */}
        <div className="relative z-[200] bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm border-b dark:border-gray-700 px-4 md:px-6 py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              {/* Hamburger menu - only on mobile */}
              <button
                onClick={() => setSidebarOpen(true)}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title="Open menu"
              >
                <Menu className="w-5 h-5 text-gray-700 dark:text-gray-300" />
              </button>
              
              <div>
                <h1 className="text-xl md:text-2xl font-bold text-gray-900 dark:text-white">Aware AI</h1>
                <p className="text-xs md:text-sm text-gray-600 dark:text-gray-400 hidden sm:block">Self-Aware RAG System with Memory Management</p>
              </div>
            </div>
            
            {/* Right side controls */}
            <div className="flex items-center gap-2 md:gap-4">
              {/* Stats Bar - hidden on small screens */}
              <div className="hidden lg:flex items-center gap-4">
                <div className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600">
                  <MessageSquare className="w-4 h-4 text-blue-500" />
                  <span className="text-gray-600 dark:text-gray-300">Messages:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stats?.session.messages_sent ?? 0}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600">
                  <Brain className="w-4 h-4 text-purple-500" />
                  <span className="text-gray-600 dark:text-gray-300">Embeddings:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stats?.lifetime?.total_embeddings ?? 0}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600">
                  <FileText className="w-4 h-4 text-green-500" />
                  <span className="text-gray-600 dark:text-gray-300">Documents:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stats?.lifetime?.documents_uploaded ?? 0}
                  </span>
                </div>
                
                <div className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600">
                  <Layers className="w-4 h-4 text-orange-500" />
                  <span className="text-gray-600 dark:text-gray-300">Threads:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stats?.lifetime?.total_threads ?? 0}
                  </span>
                </div>
                
                {stats?.memory?.using_fallback && (
                  <span className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/30 px-2 py-1 rounded border border-amber-200 dark:border-amber-700">
                    Memory Fallback
                  </span>
                )}
              </div>
              
              {/* Export button */}
              <div className="relative">
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                  title="Export conversation"
                  disabled={loadedMessages.length === 0}
                >
                  <Download className={`w-5 h-5 ${loadedMessages.length === 0 ? 'text-gray-300 dark:text-gray-600' : 'text-gray-700 dark:text-gray-300'}`} />
                </button>
                
                {/* Export dropdown */}
                {showExportMenu && (
                  <>
                    <div 
                      className="fixed inset-0 z-40"
                      onClick={() => setShowExportMenu(false)}
                    />
                    <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-1 z-[100]">
                      <button
                        onClick={exportAsJSON}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        Export as JSON
                      </button>
                      <button
                        onClick={exportAsMarkdown}
                        className="w-full px-4 py-2 text-left text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                      >
                        Export as Markdown
                      </button>
                    </div>
                  </>
                )}
              </div>
              
              {/* Dark mode toggle */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {theme === 'dark' ? (
                  <Sun className="w-5 h-5 text-yellow-500" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-700" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 overflow-hidden p-2 md:p-4">
          <div className="h-full bg-white dark:bg-gray-800 rounded-lg shadow-xl">
            <ChatInterface 
              conversationId={conversationId}
              onConversationChange={setConversationId}
              onMessageSent={handleMessageSent}
              initialMessages={loadedMessages}
            />
          </div>
        </div>
      </div>
      
      {/* Keyboard shortcuts hint - shown on larger screens */}
      <div className="hidden xl:flex fixed bottom-4 right-4 text-xs text-gray-400 dark:text-gray-600 items-center gap-1">
        <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded border dark:border-gray-700">Ctrl + K</kbd>
        <span>New chat</span>
        <span className="mx-2">|</span>
        <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded border dark:border-gray-700">Ctrl + /</kbd>
        <span>Focus input</span>
      </div>
    </main>
  )
}
