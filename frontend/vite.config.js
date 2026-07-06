import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Frontend code calls the API via plain relative paths (see src/api.js)
    // since in production FastAPI serves both frontend and API from one
    // origin. In dev, Vite runs on a different port than uvicorn, so these
    // same paths get proxied to the backend instead.
    proxy: {
      '/upload': 'http://localhost:8000',
      '/ask': 'http://localhost:8000',
      '/session': 'http://localhost:8000',
    },
  },
})
