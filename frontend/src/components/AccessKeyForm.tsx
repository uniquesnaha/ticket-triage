import { useState, type FormEvent } from 'react'
import { KeyRound } from 'lucide-react'

interface AccessKeyFormProps {
  onSubmit: (key: string) => void
}

export function AccessKeyForm({ onSubmit }: AccessKeyFormProps) {
  const [value, setValue] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  return (
    <form className="access-key-form" onSubmit={handleSubmit}>
      <label htmlFor="access-key" className="access-key-label">
        <KeyRound size={16} /> Access key
      </label>
      <div className="access-key-row">
        <input
          id="access-key"
          type="password"
          className="access-key-input"
          placeholder="Enter the triage API access key"
          autoComplete="off"
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <button type="submit" className="btn btn-primary" disabled={!value.trim()}>
          Continue
        </button>
      </div>
      <p className="access-key-hint">Stored only in this browser tab and sent as the X-API-Key header.</p>
    </form>
  )
}
