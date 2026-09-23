import { Link } from 'react-router-dom'

interface NotFoundPageProps {
  title?: string
  message?: string
}

export function NotFoundPage({
  title = 'Page not found',
  message = 'The address may be mistyped, or the page has moved.',
}: NotFoundPageProps) {
  return (
    <div className="page page--narrow">
      <div className="empty">
        <h1>{title}</h1>
        <p>{message}</p>
        <Link to="/" className="btn btn-secondary">
          Go to New triage
        </Link>
      </div>
    </div>
  )
}
