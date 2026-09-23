import type { Priority } from '../types/triage'
import { PRIORITY_LABEL } from '../lib/labels'

export function PriorityTag({ priority }: { priority: Priority }) {
  return (
    <span className={`priority priority--${priority}`}>
      <span className="priority-bars" aria-hidden="true">
        <i />
        <i />
        <i />
      </span>
      {PRIORITY_LABEL[priority]}
    </span>
  )
}

export function ReviewTag() {
  return <span className="tag tag--review">Needs review</span>
}
