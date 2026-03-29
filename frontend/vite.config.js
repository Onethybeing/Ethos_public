import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/feed': 'http://localhost:8000',
      '/article': 'http://localhost:8000',
      '/auth': 'http://localhost:8000',
      '/pnc': 'http://localhost:8000',
      '/fact-check': 'http://localhost:8000',
      '/leaderboard': 'http://localhost:8000',
      '/personalized_feed': 'http://localhost:8000',
    },
  },
})
