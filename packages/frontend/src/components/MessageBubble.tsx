'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'

interface MessageBubbleProps {
  message: {
    role: 'user' | 'assistant'
    content: string
    timestamp?: string
  }
  isStreaming?: boolean
  isTyping?: boolean
}

// Typing indicator component with animated dots
function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
    </div>
  )
}

// Helper to format relative time
function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffSecs / 60)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSecs < 60) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  
  return date.toLocaleDateString()
}

// Code block component with syntax highlighting and copy button
function CodeBlock({ language, children }: { language: string; children: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group my-2">
      {/* Language label and copy button */}
      <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-3 py-1 bg-gray-800 rounded-t-lg text-xs text-gray-400">
        <span>{language || 'code'}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 px-2 py-1 rounded hover:bg-gray-700 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-green-400" />
              <span className="text-green-400">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      
      {/* Code content */}
      <SyntaxHighlighter
        language={language || 'text'}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: '0.5rem',
          paddingTop: '2.5rem',
          fontSize: '0.875rem',
        }}
        wrapLongLines
      >
        {children}
      </SyntaxHighlighter>
    </div>
  )
}

// Inline code component
function InlineCode({ children }: { children: React.ReactNode }) {
  return (
    <code className="px-1.5 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-sm font-mono text-gray-800 dark:text-gray-200">
      {children}
    </code>
  )
}

export default function MessageBubble({ message, isStreaming, isTyping }: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const [showTimestamp, setShowTimestamp] = useState(false)
  const isUser = message.role === 'user'

  const handleCopyMessage = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div 
      className={`flex ${isUser ? 'justify-end' : 'justify-start'} group`}
      onMouseEnter={() => setShowTimestamp(true)}
      onMouseLeave={() => setShowTimestamp(false)}
    >
      <div className="flex flex-col max-w-[85%] md:max-w-[80%]">
        {/* Message bubble */}
        <div
          className={`relative rounded-lg px-4 py-3 ${
            isUser
              ? 'bg-primary-600 text-white'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
          }`}
        >
          {/* Copy full response button - only on assistant messages with content */}
          {!isUser && !isStreaming && !isTyping && message.content && (
            <button
              onClick={handleCopyMessage}
              className="absolute -top-2 -right-2 p-1.5 bg-white dark:bg-gray-600 rounded-full shadow-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-100 dark:hover:bg-gray-500"
              title="Copy message"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <Copy className="w-3.5 h-3.5 text-gray-500 dark:text-gray-300" />
              )}
            </button>
          )}
          
          {/* Typing indicator */}
          {isTyping && <TypingIndicator />}
          
          {/* Message content with markdown */}
          {!isTyping && (
          <div className={`prose prose-sm max-w-none ${
            isUser 
              ? 'prose-invert' 
              : 'dark:prose-invert'
          }`}>
            <ReactMarkdown
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '')
                  const codeString = String(children).replace(/\n$/, '')
                  
                  // Check if it's a code block (has language class or contains newlines)
                  const isCodeBlock = match || codeString.includes('\n')
                  
                  if (isCodeBlock) {
                    return (
                      <CodeBlock language={match ? match[1] : ''}>
                        {codeString}
                      </CodeBlock>
                    )
                  }
                  
                  return <InlineCode>{children}</InlineCode>
                },
                // Style headings
                h1: ({ children }) => (
                  <h1 className="text-xl font-bold mt-4 mb-2 first:mt-0">{children}</h1>
                ),
                h2: ({ children }) => (
                  <h2 className="text-lg font-semibold mt-3 mb-2 first:mt-0">{children}</h2>
                ),
                h3: ({ children }) => (
                  <h3 className="text-base font-semibold mt-2 mb-1 first:mt-0">{children}</h3>
                ),
                // Style paragraphs
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
                ),
                // Style lists
                ul: ({ children }) => (
                  <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="leading-relaxed">{children}</li>
                ),
                // Style links
                a: ({ href, children }) => (
                  <a 
                    href={href} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-600 underline"
                  >
                    {children}
                  </a>
                ),
                // Style blockquotes
                blockquote: ({ children }) => (
                  <blockquote className="border-l-4 border-gray-300 dark:border-gray-500 pl-4 italic my-2">
                    {children}
                  </blockquote>
                ),
                // Style strong/bold
                strong: ({ children }) => (
                  <strong className="font-semibold">{children}</strong>
                ),
                // Style emphasis/italic
                em: ({ children }) => (
                  <em className="italic">{children}</em>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
          )}
          
          {/* Streaming indicator */}
          {isStreaming && (
            <span className="inline-block w-2 h-4 bg-current animate-pulse ml-1" />
          )}
        </div>
        
        {/* Timestamp */}
        {message.timestamp && (showTimestamp || !isStreaming) && (
          <span className={`text-xs text-gray-400 mt-1 ${
            isUser ? 'text-right' : 'text-left'
          } ${showTimestamp ? 'opacity-100' : 'opacity-0'} transition-opacity`}>
            {formatRelativeTime(message.timestamp)}
          </span>
        )}
      </div>
    </div>
  )
}
