'use client'

import { useState, useEffect, useCallback } from 'react'
import { Plus, MessageSquare, Trash2, X, Brain, FileText, Layers } from 'lucide-react'
import { API_BASE } from '@/lib/api'

interface Thread {
  id: string
  title: string
  created_at: string
  updated_at: string
}

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

interface ThreadSidebarProps {
  currentThreadId: string | null
  onSelectThread: (threadId: string | null) => void
  onNewChat: () => void
  refreshTrigger?: number
  isOpen: boolean
  onClose: () => void
  stats?: SessionStats | null
}

// Helper to group threads by date
function groupThreadsByDate(threads: Thread[]): Record<string, Thread[]> {
  const groups: Record<string, Thread[]> = {
    'Today': [],
    'Yesterday': [],
    'Previous 7 Days': [],
    'Older': []
  }
  
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000)
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000)
  
  threads.forEach(thread => {
    const threadDate = new Date(thread.updated_at || thread.created_at)
    
    if (threadDate >= today) {
      groups['Today'].push(thread)
    } else if (threadDate >= yesterday) {
      groups['Yesterday'].push(thread)
    } else if (threadDate >= weekAgo) {
      groups['Previous 7 Days'].push(thread)
    } else {
      groups['Older'].push(thread)
    }
  })
  
  return groups
}

export default function ThreadSidebar({
  currentThreadId,
  onSelectThread,
  onNewChat,
  refreshTrigger = 0,
  isOpen,
  onClose,
  stats
}: ThreadSidebarProps) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [loading, setLoading] = useState(true)
  const [hoveredThread, setHoveredThread] = useState<string | null>(null)
  const [isPersistent, setIsPersistent] = useState(false)

  // Fetch threads from backend
  const fetchThreads = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/threads`)
      if (response.ok) {
        const data = await response.json()
        setThreads(data.threads || [])
        setIsPersistent(data.is_persistent || false)
      }
    } catch (error) {
      console.error('Failed to fetch threads:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Fetch on mount and when refreshTrigger changes
  useEffect(() => {
    fetchThreads()
  }, [fetchThreads, refreshTrigger])

  // Delete a thread
  const handleDelete = async (e: React.MouseEvent, threadId: string) => {
    e.stopPropagation()
    
    if (!confirm('Delete this conversation?')) return
    
    try {
      const response = await fetch(`${API_BASE}/api/threads/${threadId}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setThreads(prev => prev.filter(t => t.id !== threadId))
        if (currentThreadId === threadId) {
          onSelectThread(null)
        }
      }
    } catch (error) {
      console.error('Failed to delete thread:', error)
    }
  }

  // Load a thread's messages
  const handleSelectThread = async (threadId: string) => {
    onSelectThread(threadId)
  }

  const groupedThreads = groupThreadsByDate(threads)

  // Handle thread selection and close sidebar on mobile
  const handleThreadSelect = (threadId: string) => {
    onSelectThread(threadId)
    onClose() // Close sidebar on mobile after selection
  }

  // Handle new chat and close sidebar on mobile
  const handleNewChat = () => {
    onNewChat()
    onClose()
  }

  return (
    <>
      {/* Backdrop overlay - only visible on mobile when sidebar is open */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <div className={`
        fixed md:relative inset-y-0 left-0 z-50
        w-64 bg-gray-900 text-white flex flex-col h-full
        transform transition-transform duration-300 ease-in-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        md:translate-x-0
        shadow-2xl md:shadow-none
      `}>
        {/* Header with close button on mobile */}
        <div className="p-3 border-b border-gray-700 flex items-center justify-between">
          <button
            onClick={handleNewChat}
            className="flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-600 hover:bg-gray-800 transition-colors"
            title="New Chat (Ctrl+K)"
          >
            <Plus className="w-4 h-4" />
            <span>New Chat</span>
            <kbd className="hidden md:inline-flex items-center ml-auto text-xs bg-gray-700 px-1.5 py-0.5 rounded text-gray-400 gap-0.5">⌘<span>+</span>K</kbd>
          </button>
          
          {/* Close button - only on mobile */}
          <button
            onClick={onClose}
            className="md:hidden ml-2 p-2 rounded-lg hover:bg-gray-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

      {/* Thread List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-gray-400 text-sm">Loading threads...</div>
        ) : threads.length === 0 ? (
          <div className="p-4 text-gray-400 text-sm">No conversations yet</div>
        ) : (
          Object.entries(groupedThreads).map(([group, groupThreads]) => {
            if (groupThreads.length === 0) return null
            
            return (
              <div key={group} className="py-2">
                <div className="px-3 py-1 text-xs text-gray-500 font-medium">
                  {group}
                </div>
                {groupThreads.map(thread => (
                  <div
                    key={thread.id}
                    onClick={() => handleThreadSelect(thread.id)}
                    onMouseEnter={() => setHoveredThread(thread.id)}
                    onMouseLeave={() => setHoveredThread(null)}
                    className={`
                      relative flex items-center gap-2 px-3 py-2 mx-2 rounded-lg cursor-pointer
                      ${currentThreadId === thread.id 
                        ? 'bg-gray-700' 
                        : 'hover:bg-gray-800'
                      }
                    `}
                  >
                    <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <span className="text-sm truncate flex-1">
                      {thread.title || 'New Chat'}
                    </span>
                    
                    {/* Delete button on hover */}
                    {hoveredThread === thread.id && (
                      <button
                        onClick={(e) => handleDelete(e, thread.id)}
                        className="absolute right-2 p-1 rounded hover:bg-gray-600 text-gray-400 hover:text-red-400"
                        title="Delete conversation"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )
          })
        )}
      </div>

        {/* Stats - shown in sidebar on smaller screens */}
        <div className="lg:hidden p-3 border-t border-gray-700">
          <div className="text-xs text-gray-500 font-medium mb-2">Stats</div>
          <div className="grid grid-cols-2 gap-2">
            <div className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-blue-400" />
              <span className="text-gray-400">Messages</span>
              <span className="ml-auto font-semibold text-white">{stats?.session.messages_sent ?? 0}</span>
            </div>
            <div className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1.5">
              <Brain className="w-3.5 h-3.5 text-purple-400" />
              <span className="text-gray-400">Embeddings</span>
              <span className="ml-auto font-semibold text-white">{stats?.lifetime?.total_embeddings ?? 0}</span>
            </div>
            <div className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1.5">
              <FileText className="w-3.5 h-3.5 text-green-400" />
              <span className="text-gray-400">Docs</span>
              <span className="ml-auto font-semibold text-white">{stats?.lifetime?.documents_uploaded ?? 0}</span>
            </div>
            <div className="flex items-center gap-2 text-xs bg-gray-800 rounded px-2 py-1.5">
              <Layers className="w-3.5 h-3.5 text-orange-400" />
              <span className="text-gray-400">Threads</span>
              <span className="ml-auto font-semibold text-white">{stats?.lifetime?.total_threads ?? 0}</span>
            </div>
          </div>
          {stats?.memory?.using_fallback && (
            <div className="mt-2 text-xs text-amber-400 bg-amber-900/30 px-2 py-1 rounded border border-amber-700">
              Memory Fallback Active
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
          {isPersistent ? (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-green-500 rounded-full"></span>
              Synced to Supabase
            </span>
          ) : (
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 bg-yellow-500 rounded-full"></span>
              Session only
            </span>
          )}
        </div>
      </div>
    </>
  )
}
