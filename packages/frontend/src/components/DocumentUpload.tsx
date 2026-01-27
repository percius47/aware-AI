'use client'

import { useState } from 'react'
import { Upload, FileText, Loader2 } from 'lucide-react'
import { uploadDocument } from '@/lib/api'

interface DocumentUploadProps {
  onUploadSuccess?: () => void
}

export default function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState<string | null>(null)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setUploadStatus('Uploading...')

    try {
      const result = await uploadDocument(file)
      setUploadStatus(`Successfully processed ${result.chunks} chunks`)
      onUploadSuccess?.()
    } catch (error) {
      setUploadStatus('Upload failed. Please try again.')
      console.error('Upload error:', error)
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
      <input
        type="file"
        id="file-upload"
        className="hidden"
        accept=".pdf,.docx,.txt,.md"
        onChange={handleFileUpload}
        disabled={isUploading}
      />
      <label
        htmlFor="file-upload"
        className="cursor-pointer flex flex-col items-center gap-2"
      >
        {isUploading ? (
          <Loader2 className="w-8 h-8 text-primary-600 animate-spin" />
        ) : (
          <Upload className="w-8 h-8 text-primary-600" />
        )}
        <span className="text-sm text-gray-600">
          {isUploading ? 'Processing...' : 'Upload Document (PDF, DOCX, TXT, MD)'}
        </span>
        {uploadStatus && (
          <span className="text-xs text-gray-500 mt-2">{uploadStatus}</span>
        )}
      </label>
    </div>
  )
}
