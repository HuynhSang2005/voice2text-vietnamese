import { defineConfig } from 'vite'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    tanstackRouter({
      target: 'react',
      autoCodeSplitting: true,
    }),
    viteReact(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Ant Design core
          antd: ['antd'],
          // Ant Design icons
          'antd-icons': ['@ant-design/icons'],
          // React ecosystem
          react: ['react', 'react-dom'],
          // TanStack libraries
          tanstack: ['@tanstack/react-router', '@tanstack/react-query'],
        },
      },
    },
  },
})
