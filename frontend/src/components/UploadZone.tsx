import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion } from 'framer-motion'
import { Upload, FileText } from 'lucide-react'
import clsx from 'clsx'

interface UploadZoneProps {
  onFile: (file: File) => void
  disabled?: boolean
}

export function UploadZone({ onFile, disabled }: UploadZoneProps) {
  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      if (acceptedFiles[0]) onFile(acceptedFiles[0])
    },
    [onFile]
  )

  const { getRootProps, getInputProps, isDragActive, isDragReject } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'], 'text/plain': ['.csv'] },
    maxFiles: 1,
    maxSize: 4 * 1024 * 1024, // matches the API limit (Vercel caps bodies at 4.5 MB)
    disabled,
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
    >
      <div
        {...getRootProps()}
        className={clsx('upload-zone', {
          'upload-zone--active': isDragActive && !isDragReject,
          'upload-zone--reject': isDragReject,
          'upload-zone--disabled': disabled,
        })}
      >
        <input {...getInputProps()} />
        <div className="upload-zone-content">
          <motion.div
            animate={isDragActive ? { scale: 1.15, rotate: 5 } : { scale: 1, rotate: 0 }}
            transition={{ type: 'spring', stiffness: 300 }}
            className="upload-icon-wrap"
          >
            {isDragReject ? (
              <FileText size={40} className="upload-icon upload-icon--reject" />
            ) : (
              <Upload size={40} className="upload-icon" />
            )}
          </motion.div>
          <div className="upload-text">
            {isDragReject ? (
              <p className="upload-title upload-title--reject">Only CSV files are accepted</p>
            ) : isDragActive ? (
              <p className="upload-title upload-title--active">Drop to analyze tickets →</p>
            ) : (
              <>
                <p className="upload-title">Drop your CSV file here</p>
                <p className="upload-subtitle">
                  or <span className="upload-link">click to browse</span>
                </p>
              </>
            )}
          </div>
          <div className="upload-requirements">
            <span>Required columns: <code>ticket_id</code>, <code>text</code></span>
            <span>·</span>
            <span>Max 50 tickets · Max 4 MB</span>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
