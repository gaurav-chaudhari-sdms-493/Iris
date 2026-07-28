import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': 'http://localhost:8008',
      '/video_feed': 'http://localhost:8008',
      '/ws': {
        target: 'ws://localhost:8008',
        ws: true
      }
    }
  }
})
