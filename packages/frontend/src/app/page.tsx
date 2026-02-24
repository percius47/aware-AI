'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import ChatInterface from '@/components/ChatInterface'
import ThreadSidebar from '@/components/ThreadSidebar'
import { MessageSquare, Brain, FileText, Layers, Menu, Moon, Sun, Download, Loader2, Trash2, X } from 'lucide-react'
import { API_BASE, fetchWithAuth } from '@/lib/api'
import { useTheme } from '@/components/ThemeProvider'
import { useAuth } from '@/components/AuthProvider'
import toast from 'react-hot-toast'

interface SessionStats {
  session: {
    messages_sent: number
    active_threads: number
  }
  lifetime: {
    total_embeddings: number
    documents_uploaded: number
    document_filenames: string[]
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
  const [showDocumentsMenu, setShowDocumentsMenu] = useState(false)
  const [deletingDoc, setDeletingDoc] = useState<string | null>(null)
  const { theme, toggleTheme } = useTheme()
  const { user, loading, signOut } = useAuth()
  const inputRef = useRef<HTMLInputElement>(null)

  // Fetch stats from backend
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/stats`)
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
    if (user) {
      fetchStats()
    }
  }, [fetchStats, messageCount, user])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl/Cmd + K - New chat
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault()
        setConversationId(null)
        setLoadedMessages([])
        toast.success('New chat started', { duration: 2000 })
      }
      
      // Ctrl/Cmd + / - Focus input
      if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('focusChatInput'))
      }
      
      // Escape - Close sidebar on mobile or close dropdowns
      if (e.key === 'Escape') {
        if (showDocumentsMenu) setShowDocumentsMenu(false)
        else if (showExportMenu) setShowExportMenu(false)
        else if (sidebarOpen) setSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sidebarOpen, showDocumentsMenu, showExportMenu])

  // Clear all state on user sign out to prevent data leakage between users
  useEffect(() => {
    const handleSignOut = () => {
      setConversationId(null)
      setStats(null)
      setMessageCount(0)
      setSidebarRefresh(0)
      setLoadedMessages([])
      setSidebarOpen(false)
      setShowExportMenu(false)
      setShowDocumentsMenu(false)
    }

    window.addEventListener('userSignOut', handleSignOut)
    return () => window.removeEventListener('userSignOut', handleSignOut)
  }, [])

  // Callback when a message is sent
  const handleMessageSent = useCallback(() => {
    setMessageCount(prev => prev + 1)
    setSidebarRefresh(prev => prev + 1)
  }, [])

  // Handle selecting a thread from sidebar
  const handleSelectThread = useCallback(async (threadId: string | null) => {
    if (!threadId) {
      setConversationId(null)
      setLoadedMessages([])
      return
    }

    try {
      const response = await fetchWithAuth(`${API_BASE}/api/threads/${threadId}`)
      if (response.ok) {
        const thread = await response.json()
        setConversationId(threadId)
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
  }, [])

  // Handle new chat
  const handleNewChat = useCallback(() => {
    setConversationId(null)
    setLoadedMessages([])
  }, [])

  // Handle data reset
  const handleDataReset = useCallback(() => {
    setLoadedMessages([])
    setConversationId(null)
    fetchStats()
  }, [fetchStats])

  // Export conversation as JSON
  const exportAsJSON = useCallback(() => {
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
  }, [loadedMessages, conversationId])

  // Export conversation as Markdown
  const exportAsMarkdown = useCallback(() => {
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
  }, [loadedMessages, conversationId])

  // Delete a specific document
  const handleDeleteDocument = useCallback(async (filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? This will remove all its embeddings from your knowledge base.`)) {
      return
    }
    
    setDeletingDoc(filename)
    try {
      const response = await fetchWithAuth(`${API_BASE}/api/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        toast.success(`Deleted "${filename}"`)
        fetchStats() // Refresh stats to update the list
      } else {
        const error = await response.json()
        toast.error(error.detail || 'Failed to delete document')
      }
    } catch (error) {
      console.error('Failed to delete document:', error)
      toast.error('Failed to delete document')
    } finally {
      setDeletingDoc(null)
    }
  }, [fetchStats])

  // Show loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
          <p className="text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    )
  }

  // Redirect to login if not authenticated
  if (!user) {
    return null
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
        onDataReset={handleDataReset}
        userEmail={user?.email}
        onSignOut={signOut}
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
                
                <div className="relative">
                  <button
                    onClick={() => setShowDocumentsMenu(!showDocumentsMenu)}
                    className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors cursor-pointer"
                    title="Click to view uploaded documents"
                  >
                    <FileText className="w-4 h-4 text-green-500" />
                    <span className="text-gray-600 dark:text-gray-300">Documents:</span>
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {stats?.lifetime?.documents_uploaded ?? 0}
                    </span>
                  </button>
                  
                  {/* Documents dropdown */}
                  {showDocumentsMenu && (
                    <>
                      <div 
                        className="fixed inset-0 z-40"
                        onClick={() => setShowDocumentsMenu(false)}
                      />
                      <div className="absolute right-0 mt-2 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-lg border dark:border-gray-700 py-2 z-[100] max-h-80 overflow-y-auto">
                        <div className="px-3 py-1 border-b dark:border-gray-700 flex items-center justify-between">
                          <span className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase">
                            Uploaded Documents
                          </span>
                          <button
                            onClick={() => setShowDocumentsMenu(false)}
                            className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                          >
                            <X className="w-3 h-3 text-gray-500" />
                          </button>
                        </div>
                        {stats?.lifetime?.document_filenames && stats.lifetime.document_filenames.length > 0 ? (
                          <ul className="py-1">
                            {stats.lifetime.document_filenames.map((filename) => (
                              <li 
                                key={filename}
                                className="px-3 py-2 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 group"
                              >
                                <span className="text-sm text-gray-700 dark:text-gray-300 truncate flex-1 mr-2" title={filename}>
                                  {filename}
                                </span>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleDeleteDocument(filename)
                                  }}
                                  disabled={deletingDoc === filename}
                                  className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/30 rounded opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-50"
                                  title={`Delete ${filename}`}
                                >
                                  {deletingDoc === filename ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <Trash2 className="w-4 h-4" />
                                  )}
                                </button>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <div className="px-3 py-4 text-center text-sm text-gray-500 dark:text-gray-400">
                            No documents uploaded yet
                          </div>
                        )}
                      </div>
                    </>
                  )}
                </div>
                
                <div className="flex items-center gap-2 text-sm bg-white dark:bg-gray-700 rounded-lg px-3 py-1.5 shadow-sm border dark:border-gray-600">
                  <Layers className="w-4 h-4 text-orange-500" />
                  <span className="text-gray-600 dark:text-gray-300">Threads:</span>
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {stats?.lifetime?.total_threads ?? 0}
                  </span>
                </div>
                
                {stats?.memory?.using_fallback && (
                  <span 
                    className="text-xs text-amber-600 bg-amber-50 dark:bg-amber-900/30 px-2 py-1 rounded border border-amber-200 dark:border-amber-700 cursor-help"
                    title="Memory is stored locally in this session only. Supabase connection unavailable - memories won't persist after restart. Check your SUPABASE_URL and SUPABASE_KEY environment variables."
                  >
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
    </main>
  )
}
