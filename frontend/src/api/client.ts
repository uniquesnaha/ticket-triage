import axios, { AxiosError } from 'axios'
import type { TriageBatchRequest, TriageBatchResponse } from '../types/triage'

// The API is served from the same origin (Vercel rewrite in production, Vite proxy in dev).
// The access key is typed in by the user and kept only for this browser tab. It is never
// embedded in the JS bundle.
const ACCESS_KEY_STORAGE = 'triage.accessKey'

export const accessKey = {
  get: (): string => sessionStorage.getItem(ACCESS_KEY_STORAGE) ?? '',
  set: (key: string): void => sessionStorage.setItem(ACCESS_KEY_STORAGE, key.trim()),
  clear: (): void => sessionStorage.removeItem(ACCESS_KEY_STORAGE),
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface ProblemDetails {
  detail?: string | { msg: string; loc?: (string | number)[] }[]
}

function toApiError(error: AxiosError<ProblemDetails>): ApiError {
  const status = error.response?.status ?? null
  const detail = error.response?.data?.detail
  let message: string
  if (typeof detail === 'string') message = detail
  else if (Array.isArray(detail)) message = detail.map((d) => d.msg).join('; ')
  else if (error.code === 'ECONNABORTED') message = 'The request timed out. Try a smaller batch.'
  else if (status === 504) message = 'The server took too long to respond. Try a smaller batch.'
  else message = error.message
  return new ApiError(message, status)
}

const apiClient = axios.create({ timeout: 90_000 })

apiClient.interceptors.request.use((config) => {
  const key = accessKey.get()
  if (key) config.headers.set('X-API-Key', key)
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ProblemDetails>) => Promise.reject(toApiError(error)),
)

export const triageAPI = {
  triageJSON: async (request: TriageBatchRequest): Promise<TriageBatchResponse> => {
    const { data } = await apiClient.post<TriageBatchResponse>('/api/v1/triage', request)
    return data
  },

  triageCSV: async (file: File): Promise<TriageBatchResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await apiClient.post<TriageBatchResponse>('/api/v1/triage/upload', formData)
    return data
  },
}
