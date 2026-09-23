import { Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { HowItWorksPage } from './pages/HowItWorksPage'
import { NewTriagePage } from './pages/NewTriagePage'
import { NotFoundPage } from './pages/NotFoundPage'
import { RunPage } from './pages/RunPage'
import { RunsPage } from './pages/RunsPage'
import { TriageProvider } from './state/TriageContext'
import './styles/index.css'

export default function App() {
  return (
    <TriageProvider>
      <Routes>
        <Route element={<AppShell />}>
          <Route index element={<NewTriagePage />} />
          <Route path="runs" element={<RunsPage />} />
          <Route path="runs/:runId" element={<RunPage />} />
          <Route path="how-it-works" element={<HowItWorksPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </TriageProvider>
  )
}
