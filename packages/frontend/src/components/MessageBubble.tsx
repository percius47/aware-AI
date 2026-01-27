'use client'

import ReactMarkdown from 'react-markdown'

interface MessageBubbleProps {
  message: {
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
  }
  isStreaming?: boolean
}

export default function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        {isStreaming && (
          <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
        )}
      </div>
    </div>
  )
}
