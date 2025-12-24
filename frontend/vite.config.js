import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    // 自动导入 Element Plus 组件
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    // 允许的主机名
    allowedHosts: 'all', // 允许所有主机访问(包括局域网IP、cloudflare tunnel等)
    // 热重载配置
    watch: {
      usePolling: true, // Docker 环境需要轮询监听文件变化
    },
    hmr: {
      host: 'localhost',
      port: 5173,
    },
    // 代理后端 API
    proxy: {
      '/api': {
        // Docker 环境使用服务名,本地开发使用 localhost
        target: process.env.VITE_PROXY_TARGET || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})

