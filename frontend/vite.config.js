import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// /api проксируем на backend (uvicorn на :8000)
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
