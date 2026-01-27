'use client'

import { useState, useEffect, useCallback } from 'react'
import { Plus, MessageSquare, Trash2, ChevronRight } from 'lucide-react'
import { API_BASE } from '@/lib/api'

interface Thread {
  id: string
  title: string
  created_at: string
  updated_at: string
}

interface ThreadSidebarProps {
  currentThreadId: string | null
  onSelectThread: (threadId: string | null) => void
  onNewChat: () => void
  refreshTrigger?: number
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
  refreshTrigger = 0
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

  return (
    <div className="w-64 bg-gray-900 text-white flex flex-col h-full">
      {/* New Chat Button */}
      <div className="p-3 border-b border-gray-700">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-600 hover:bg-gray-800 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>New Chat</span>
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
                    onClick={() => handleSelectThread(thread.id)}
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
  )
}
