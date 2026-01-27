import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL || 'https://aware-ai-rag.vercel.app'),
  title: 'Aware AI - Intelligent Chat with Persistent Memory',
  description: 'An AI assistant that remembers your conversations, understands your documents, and learns from every interaction. Built with RAG technology for context-aware responses.',
  keywords: ['AI', 'chatbot', 'RAG', 'memory', 'documents', 'assistant', 'intelligent', 'conversation'],
  authors: [{ name: 'Aware AI' }],
  openGraph: {
    title: 'Aware AI - Intelligent Chat with Persistent Memory',
    description: 'AI assistant with document understanding and conversation memory. Upload documents, ask questions, and get context-aware responses.',
    type: 'website',
    siteName: 'Aware AI',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Aware AI - Intelligent Chat with Persistent Memory',
    description: 'AI assistant with document understanding and conversation memory.',
  },
  robots: {
    index: true,
    follow: true,
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🧠</text></svg>" />
      </head>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
