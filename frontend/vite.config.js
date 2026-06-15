import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.PORT) || 3010,
    proxy: {
      '/api': { target: process.env.VITE_API_URL || 'http://localhost:8010', changeOrigin: true },
    },
  },
});
