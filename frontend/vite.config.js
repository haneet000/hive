import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Target 'http://backend:8000' inside Docker, fallback to 'http://127.0.0.1:8000' for local dev
const target = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: target,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '')
      }
    }
  }
})
