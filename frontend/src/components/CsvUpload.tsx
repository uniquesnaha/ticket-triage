import { useCallback, useState } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { FileCsvIcon, UploadSimpleIcon } from '@phosphor-icons/react'
import clsx from 'clsx'

const MAX_BYTES = 4 * 1024 * 1024 // matches the API limit (Vercel caps bodies at 4.5 MB)

export function CsvUpload({ onFile }: { onFile: (file: File) => void }) {
  const [rejection, setRejection] = useState<string | null>(null)
  const [loadingSample, setLoadingSample] = useState(false)

  const onDrop = useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const code = rejected[0].errors[0]?.code
        setRejection(
          code === 'file-too-large'
            ? 'That file is over 4 MB. Split it into smaller batches.'
            : 'Only .csv files are accepted.',
        )
        return
      }
      setRejection(null)
      if (accepted[0]) onFile(accepted[0])
    },
    [onFile],
  )

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    maxSize: MAX_BYTES,
    noClick: true,
  })

  const useSample = async () => {
    setLoadingSample(true)
    try {
      const response = await fetch('/project_1.csv')
      if (!response.ok) throw new Error()
      const blob = await response.blob()
      onFile(new File([blob], 'project_1.csv', { type: 'text/csv' }))
    } catch {
      setRejection('Could not load the sample file.')
    } finally {
      setLoadingSample(false)
    }
  }

  return (
    <div>
      <div {...getRootProps({ className: clsx('dropzone', isDragActive && 'dropzone--active') })}>
        <input {...getInputProps()} aria-label="CSV file" />
        <FileCsvIcon size={28} weight="light" className="dropzone-icon" />
        <p className="dropzone-title">
          {isDragActive ? 'Drop to start triage' : 'Drag a CSV file here'}
        </p>
        <p className="dropzone-hint">
          Needs <code>ticket_id</code> and <code>text</code> columns. Up to 50 tickets, 4 MB.
        </p>
        <div className="dropzone-actions">
          <button type="button" className="btn btn-primary" onClick={open}>
            <UploadSimpleIcon size={16} weight="bold" />
            Choose file
          </button>
          <button
            type="button"
            className="btn btn-quiet"
            onClick={useSample}
            disabled={loadingSample}
          >
            Try the sample (10 tickets)
          </button>
        </div>
      </div>
      {rejection && (
        <p className="inline-error" role="alert">
          {rejection}
        </p>
      )}

      <section className="csv-format" aria-labelledby="csv-format-title">
        <div className="section-head">
          <h2 id="csv-format-title">Expected format</h2>
          <a href="/project_1.csv" download className="link-btn">
            Download sample
          </a>
        </div>
        <pre>{`ticket_id,text
T001,"I was charged twice for order 8841. Please refund the duplicate charge."
T002,"Can't log in after resetting my password."`}</pre>
        <p>
          Header names are case-insensitive and extra columns are ignored. Rows with missing text or
          IDs are still triaged and flagged for review instead of failing the file.
        </p>
      </section>
    </div>
  )
}
