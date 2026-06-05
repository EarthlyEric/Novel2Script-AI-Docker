import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

/**
 * Vite 构建配置
 *
 * 配置项说明：
 * - plugin: Vue3 单文件组件支持
 * - resolve.alias: 路径别名 @ 指向 src 目录
 * - server.proxy: 开发环境代理 /api 到后端 8000 端口
 */
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
