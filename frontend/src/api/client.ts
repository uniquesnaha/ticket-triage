import axios from 'axios'
import type { TriageBatchRequest, TriageBatchResponse } from '../types/triage'

const API_URL = import.meta.env.VITE_API_URL ?? ''
const API_KEY = import.meta.env.VITE_API_KEY ?? ''

const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 120_000, // 2 minutes for large batches
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  },
})

// Response interceptor for error normalization
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail ?? error.message
    return Promise.reject(new Error(detail))
  }
)

export const triageAPI = {
  triageJSON: async (request: TriageBatchRequest): Promise<TriageBatchResponse> => {
    const { data } = await apiClient.post<TriageBatchResponse>('/api/v1/triage', request)
    return data
  },

  triageCSV: async (file: File): Promise<TriageBatchResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    const { data } = await apiClient.post<TriageBatchResponse>('/api/v1/triage/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  health: async () => {
    const { data } = await apiClient.get('/api/v1/health')
    return data
  },
}
