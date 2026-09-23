import { useCallback, useState } from 'react'
import { useDropzone, type FileRejection } from 'react-dropzone'
import { FileCsvIcon, UploadSimpleIcon } from '@phosphor-icons/react'
import clsx from 'clsx'
import { Composer } from './Composer'

const MAX_BYTES = 4 * 1024 * 1024 // matches the API limit (Vercel caps bodies at 4.5 MB)

interface IntakeProps {
  onFile: (file: File) => void
  disabled: boolean
}

type Mode = 'csv' | 'text'

export function Intake({ onFile, disabled }: IntakeProps) {
  const [mode, setMode] = useState<Mode>('csv')
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
    disabled,
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
    <section className="intake" aria-labelledby="intake-title">
      <h1 id="intake-title">Triage support tickets</h1>
      <p className="intake-lede">
        Each ticket gets a category, priority, sentiment, customer impact and a review flag. You
        can see where the model decided and where a rule stepped in.
      </p>

      <div className="segmented intake-tabs" role="tablist" aria-label="Input">
        {(
          [
            ['csv', 'Upload a CSV'],
            ['text', 'Write a ticket'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            role="tab"
            id={`tab-${id}`}
            aria-selected={mode === id}
            aria-controls={`panel-${id}`}
            className={clsx('segment', mode === id && 'segment--active')}
            onClick={() => setMode(id)}
          >
            {label}
          </button>
        ))}
      </div>

      <div id="panel-text" role="tabpanel" aria-labelledby="tab-text" hidden={mode !== 'text'}>
        <Composer />
      </div>

      <div id="panel-csv" role="tabpanel" aria-labelledby="tab-csv" hidden={mode !== 'csv'}>
        <div
          {...getRootProps({
            className: clsx('dropzone', isDragActive && 'dropzone--active'),
          })}
        >
          <input {...getInputProps()} aria-label="CSV file" />
          <FileCsvIcon size={28} weight="light" className="dropzone-icon" />
          <p className="dropzone-title">
            {isDragActive ? 'Drop to start triage' : 'Drag a CSV file here'}
          </p>
          <p className="dropzone-hint">
            Needs <code>ticket_id</code> and <code>text</code> columns. Up to 50 tickets, 4 MB.
          </p>
          <div className="dropzone-actions">
            <button type="button" className="btn btn-primary" onClick={open} disabled={disabled}>
              <UploadSimpleIcon size={16} weight="bold" />
              Choose file
            </button>
            <button
              type="button"
              className="btn btn-quiet"
              onClick={useSample}
              disabled={disabled || loadingSample}
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
      </div>

      <dl className="intake-notes">
        <div>
          <dt>Model judgment</dt>
          <dd>An LLM classifies each ticket against a fixed schema and cites the ticket text.</dd>
        </div>
        <div>
          <dt>Rule checks</dt>
          <dd>
            Explicit evidence, like &ldquo;charged twice&rdquo; or &ldquo;not urgent&rdquo;,
            overrides the model. Every change is recorded.
          </dd>
        </div>
        <div>
          <dt>Human review</dt>
          <dd>Security, payment and ambiguous tickets are flagged instead of auto-routed.</dd>
        </div>
      </dl>
    </section>
  )
}
