/**
 * 应用入口文件
 *
 * 初始化 Vue3 应用实例，注册全局插件：
 * - Element Plus UI 组件库
 * - Element Plus 图标库
 * - Vue Router 路由管理
 */
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)

// 注册所有 Element Plus 图标
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

app.use(ElementPlus)
app.use(router)
app.mount('#app')
