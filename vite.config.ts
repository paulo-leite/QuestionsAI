import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/documents': 'http://localhost:8000',
      '/questions': 'http://localhost:8000',
      '/research': 'http://localhost:8000',
    },
  },
})
