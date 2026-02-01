import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const envBase = process.env.VITE_BASE?.trim();
const base = envBase ? (envBase.endsWith('/') ? envBase : `${envBase}/`) : './';

// https://vitejs.dev/config/
export default defineConfig({
  base,
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/static': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
