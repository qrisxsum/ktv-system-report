import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  // 解决 Docker 重启后浏览器强缓存导致的 deps 分块 404/白屏问题：
  // 默认 cacheDir 是 node_modules/.vite，Vite 会给 deps 资源加一年期 immutable 缓存。
  // 容器重建/依赖预构建变化时，浏览器可能复用旧缓存 URL，出现 chunk 不存在。
  // 用项目专用 cacheDir 可以让 URL 路径变化，从而自然失效旧缓存。
  cacheDir: 'node_modules/.vite-ktv',
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
        target: process.env.VITE_API_BASE_URL || 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
})

