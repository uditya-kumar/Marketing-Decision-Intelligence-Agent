import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    // React 19 + React Compiler. In @vitejs/plugin-react v6 (Vite 8 / rolldown)
    // the compiler is enabled natively via `compiler` instead of a Babel plugin.
    react({ compiler: true }),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': path.resolve(import.meta.dirname, './src'),
    },
  },
})
