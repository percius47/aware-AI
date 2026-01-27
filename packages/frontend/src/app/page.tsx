'use client'

import { useState, useEffect, useCallback } from 'react'
import ChatInterface from '@/components/ChatInterface'
import ThreadSidebar from '@/components/ThreadSidebar'
import { MessageSquare, Brain, FileText, Layers } from 'lucide-react'

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
}

export default function Home() {
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [stats, setStats] = useState<SessionStats | null>(null)
  const [messageCount, setMessageCount] = useState(0)
  const [sidebarRefresh, setSidebarRefresh] = useState(0)
  const [loadedMessages, setLoadedMessages] = useState<Message[]>([])

  // Fetch stats from backend
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/api/stats')
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
      const response = await fetch(`http://localhost:8000/api/threads/${threadId}`)
      if (response.ok) {
        const thread = await response.json()
        setConversationId(threadId)
        // Convert messages to the format ChatInterface expects
        const messages = (thread.messages || []).map((m: any) => ({
          role: m.role as 'user' | 'assistant',
          content: m.content
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

  return (
    <main className="h-screen flex bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Sidebar */}
      <ThreadSidebar
        currentThreadId={conversationId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        refreshTrigger={sidebarRefresh}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header with stats */}
        <div className="bg-white/80 backdrop-blur-sm border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Aware AI</h1>
              <p className="text-sm text-gray-600">Self-Aware RAG System with Memory Management</p>
            </div>
            
            {/* Stats Bar */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm bg-white rounded-lg px-3 py-1.5 shadow-sm border">
                <MessageSquare className="w-4 h-4 text-blue-500" />
                <span className="text-gray-600">Messages:</span>
                <span className="font-semibold text-gray-900">
                  {stats?.session.messages_sent ?? 0}
                </span>
              </div>
              
              <div className="flex items-center gap-2 text-sm bg-white rounded-lg px-3 py-1.5 shadow-sm border">
                <Brain className="w-4 h-4 text-purple-500" />
                <span className="text-gray-600">Embeddings:</span>
                <span className="font-semibold text-gray-900">
                  {stats?.lifetime?.total_embeddings ?? 0}
                </span>
              </div>
              
              <div className="flex items-center gap-2 text-sm bg-white rounded-lg px-3 py-1.5 shadow-sm border">
                <FileText className="w-4 h-4 text-green-500" />
                <span className="text-gray-600">Documents:</span>
                <span className="font-semibold text-gray-900">
                  {stats?.lifetime?.documents_uploaded ?? 0}
                </span>
              </div>
              
              <div className="flex items-center gap-2 text-sm bg-white rounded-lg px-3 py-1.5 shadow-sm border">
                <Layers className="w-4 h-4 text-orange-500" />
                <span className="text-gray-600">Threads:</span>
                <span className="font-semibold text-gray-900">
                  {stats?.lifetime?.total_threads ?? 0}
                </span>
              </div>
              
              {stats?.memory?.using_fallback && (
                <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded border border-amber-200">
                  Memory Fallback
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 overflow-hidden p-4">
          <div className="h-full bg-white rounded-lg shadow-xl">
            <ChatInterface 
              key={conversationId || 'new-chat'}
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
