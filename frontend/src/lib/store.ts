import { useSyncExternalStore } from 'react'
import type { TriageBatchResponse, TriageResult } from '../types/triage'

// Runs and quick checks are kept in this browser only (localStorage). Nothing is
// stored server-side: the app has no accounts, so shared storage would expose one
// user's tickets to everyone else.

export interface Run {
  id: string
  name: string
  createdAt: string
  response: TriageBatchResponse
}

function createListStore<T>(key: string, maxItems: number) {
  let cache: T[] | null = null
  const listeners = new Set<() => void>()
  const emit = () => listeners.forEach((listener) => listener())

  const read = (): T[] => {
    if (cache) return cache
    try {
      const raw = localStorage.getItem(key)
      cache = raw ? (JSON.parse(raw) as T[]) : []
    } catch {
      cache = []
    }
    return cache
  }

  const write = (items: T[]) => {
    let kept = items.slice(0, maxItems)
    // On quota errors, drop the oldest entries until the list fits.
    for (;;) {
      try {
        localStorage.setItem(key, JSON.stringify(kept))
        break
      } catch {
        if (kept.length <= 1) break
        kept = kept.slice(0, -1)
      }
    }
    cache = kept
    emit()
  }

  window.addEventListener('storage', (event) => {
    if (event.key === key) {
      cache = null
      emit()
    }
  })

  return {
    subscribe(listener: () => void) {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
    getSnapshot: read,
    prepend(item: T) {
      write([item, ...read()])
    },
    replace(items: T[]) {
      write(items)
    },
  }
}

const runStore = createListStore<Run>('triage.runs.v1', 25)
const quickCheckStore = createListStore<TriageResult>('triage.quick-checks.v1', 50)

export function useRuns(): Run[] {
  return useSyncExternalStore(runStore.subscribe, runStore.getSnapshot)
}

export function useQuickChecks(): TriageResult[] {
  return useSyncExternalStore(quickCheckStore.subscribe, quickCheckStore.getSnapshot)
}

export function saveRun(name: string, response: TriageBatchResponse): Run {
  const run: Run = {
    id: `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    name,
    createdAt: new Date().toISOString(),
    response,
  }
  runStore.prepend(run)
  return run
}

export function deleteRun(id: string) {
  runStore.replace(runStore.getSnapshot().filter((run) => run.id !== id))
}

export function saveQuickCheck(result: TriageResult) {
  quickCheckStore.prepend(result)
}

export function clearQuickChecks() {
  quickCheckStore.replace([])
}

const relative = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' })

export function formatRelative(iso: string): string {
  const seconds = Math.round((new Date(iso).getTime() - Date.now()) / 1000)
  const abs = Math.abs(seconds)
  if (abs < 45) return 'just now'
  if (abs < 3600) return relative.format(Math.round(seconds / 60), 'minute')
  if (abs < 86400) return relative.format(Math.round(seconds / 3600), 'hour')
  if (abs < 86400 * 7) return relative.format(Math.round(seconds / 86400), 'day')
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
